"""Generate editable Power BI project files from the published CSV contracts.

Run from repository root: python scripts/build_powerbi.py
Requires a Windows Power BI Desktop refresh for runtime validation.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PBI = ROOT / 'powerbi'
REPORT = PBI / 'RetailSignal.Report'
MODEL = PBI / 'RetailSignal.SemanticModel'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def schema(kind):
    return BASE + kind + '/1.0.0/schema.json'


# The folder parameter is the only machine-specific setting. Do not embed the
# author's absolute home path in the public model.
tables = []
contracts = {
    'Date': ('dim_date', {'date_key':'dateTime','year':'int64','month_number':'int64','month':'string','weekday':'string'}),
    'Country': ('dim_country', {'country':'string'}),
    'DailyRevenue': ('mart_daily_country', {'date_key':'dateTime','country':'string','gross_revenue':'double','credits':'double','net_revenue':'double','orders':'int64','known_customers':'int64','anonymous_gross':'double','line_count':'int64'}),
    'Cohorts': ('mart_cohorts', {'cohort':'string','month_index':'int64','cohort_size':'int64','active_customers':'int64','retention':'double'}),
    'Customers': ('customer_scores', {'customer_id':'string','orders_180d':'int64','gross_180d':'double','products_180d':'int64','active_days_180d':'int64','recency_days':'double','tenure_days':'double','aov_180d':'double','orders_30d':'int64','credits_180d':'double','credit_ratio':'double','as_of':'dateTime','segment':'string','repeat_probability':'double','priority_rank':'int64'})
}
measures = {
    'DailyRevenue': [
        ('Gross Revenue','SUM(DailyRevenue[gross_revenue])','£#,0.00'),
        ('Credits','SUM(DailyRevenue[credits])','£#,0.00'),
        ('Net Revenue','[Gross Revenue] - [Credits]','£#,0.00'),
        ('Credit Ratio','DIVIDE([Credits], [Gross Revenue])','0.0%'),
        ('Sales Orders','SUM(DailyRevenue[orders])','#,0'),
        ('Average Order Value','DIVIDE([Gross Revenue], [Sales Orders])','£#,0.00'),
        ('Identified Revenue Share','1 - DIVIDE(SUM(DailyRevenue[anonymous_gross]), [Gross Revenue])','0.0%'),
        ('Prior Month Net','CALCULATE([Net Revenue], DATEADD(\'Date\'[date_key], -1, MONTH))','£#,0.00'),
        ('Net MoM Growth','DIVIDE([Net Revenue] - [Prior Month Net], [Prior Month Net])','0.0%'),
    ],
    'Cohorts': [
        ('Cohort Retention','IF(HASONEVALUE(Cohorts[month_index]), DIVIDE(SUM(Cohorts[active_customers]), SUM(Cohorts[cohort_size])))','0.0%')
    ],
    'Customers': [
        ('Scored Customers','COUNTROWS(Customers)','#,0'),
        ('Mean Repeat Propensity','AVERAGE(Customers[repeat_probability])','0.0%'),
        ('Historical Customer Gross','SUM(Customers[gross_180d])','£#,0.00')
    ]
}
for name, (filename, columns) in contracts.items():
    types = {'dateTime':'type date','int64':'Int64.Type','double':'type number','string':'type text'}
    pairs = ', '.join('{"' + col + '", ' + types[typ] + '}' for col,typ in columns.items())
    expr = ['let', f'    Source = Csv.Document(File.Contents(DataFolder & "/{filename}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
            '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
            f'    Typed = Table.TransformColumnTypes(Headers, {{{pairs}}}, "en-GB")', 'in', '    Typed']
    table = {'name':name, 'columns':[{'name':col,'dataType':typ,'sourceColumn':col,'summarizeBy':'none',
                **({'isHidden':True} if name=='DailyRevenue' and col=='known_customers' else {})} for col,typ in columns.items()],
             'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':expr}}]}
    if name in measures:
        table['measures'] = [{'name':n,'expression':e,'formatString':f} for n,e,f in measures[name]]
    if name=='Date':
        table['columns'][0]['isKey']=True
        table['columns'][0]['formatString']='yyyy-MM-dd'
        table['dataCategory']='Time'
    tables.append(table)
model = {'name':'RetailSignal','compatibilityLevel':1600,'model':{
    'culture':'en-GB','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-GB',
    'expressions':[{'name':'DataFolder','kind':'m','expression':'"C:/retailsignal/data/exports" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'}],
    'tables':tables,'relationships':[
        {'name':'DailyRevenue_Date','fromTable':'DailyRevenue','fromColumn':'date_key','toTable':'Date','toColumn':'date_key','crossFilteringBehavior':'oneDirection'},
        {'name':'DailyRevenue_Country','fromTable':'DailyRevenue','fromColumn':'country','toTable':'Country','toColumn':'country','crossFilteringBehavior':'oneDirection'}]}}
write(MODEL/'model.bim',model)
write(MODEL/'definition.pbism',{'version':'1.0','settings':{}})
write(PBI/'RetailSignal.pbip',{'version':'1.0','artifacts':[{'report':{'path':'RetailSignal.Report'}}],'settings':{'enableAutoRecovery':True}})
write(REPORT/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byPath':{'path':'../RetailSignal.SemanticModel'}}})
write(REPORT/'definition/version.json',{'$schema':schema('versionMetadata'),'version':'4.0.0'})
write(REPORT/'definition/report.json',{'$schema':schema('report'),'layoutOptimization':'None','themeCollection':{}})


def literal(value):
    if isinstance(value,bool): v='true' if value else 'false'
    elif isinstance(value,str): v="'"+value.replace("'","''")+"'"
    else: v=str(value)+'D'
    return {'expr':{'Literal':{'Value':v}}}


def field(table, column, measure=False):
    return {'field':{'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':column}},
            'queryRef':f'{table}.{column}', 'nativeQueryRef':column}


def visual(page,name,kind,title,x,y,w,h,roles):
    query={k:{'projections':v} for k,v in roles.items()}
    cfg={'visualType':kind, 'query':{'queryState':query}, 'visualContainerObjects':{
        'title':[{'properties':{'show':literal(True),'text':literal(title),'fontSize':literal(15),'fontColor':{'solid':{'color':literal('#173442')}}}}],
        'background':[{'properties':{'show':literal(True),'color':{'solid':{'color':literal('#FFFFFF')}},'transparency':literal(0)}}]}}
    write(REPORT/f'definition/pages/{page}/visuals/{name}/visual.json',{
        '$schema':schema('visualContainer'),'name':name,'position':{'x':x,'y':y,'width':w,'height':h,'z':y+x,'tabOrder':y+x},'visual':cfg})


pages=[('revenue','Revenue | GBP | Dec 2011 partial'),('retention','Retention | Complete months | All markets'),('customers','Propensity | Dec 10 2011 | Not causal uplift')]
for p,title in pages:
    write(REPORT/f'definition/pages/{p}/page.json',{'$schema':schema('page'),'name':p,'displayName':title,'displayOption':'FitToPage','width':1280,'height':720})
write(REPORT/'definition/pages/pages.json',{'$schema':schema('pagesMetadata'),'pageOrder':[p for p,_ in pages],'activePageName':'revenue'})
for i,m in enumerate(['Net Revenue','Gross Revenue','Credit Ratio','Sales Orders']):
    visual('revenue',f'kpi{i}','card',m,20+i*315,20,300,120,{'Values':[field('DailyRevenue',m,True)]})
visual('revenue','trend','lineChart','Monthly revenue • December 2011 is partial',20,160,800,330,
       {'Category':[field('Date','month')],'Y':[field('DailyRevenue','Gross Revenue',True),field('DailyRevenue','Net Revenue',True)]})
visual('revenue','markets','clusteredBarChart','Net revenue by country',840,160,420,330,
       {'Category':[field('Country','country')],'Y':[field('DailyRevenue','Net Revenue',True)]})
visual('revenue','countryfilter','slicer','Choose markets',20,510,400,180,{'Values':[field('Country','country')]})
visual('revenue','datefilter','slicer','Choose dates',440,510,400,180,{'Values':[field('Date','date_key')]})
visual('revenue','coverage','card','Identified share of gross revenue',860,510,400,180,{'Values':[field('DailyRevenue','Identified Revenue Share',True)]})
visual('retention','cohorts','pivotTable','Cohort retention • blanks are unobserved months',20,20,1240,480,
       {'Rows':[field('Cohorts','cohort')],'Columns':[field('Cohorts','month_index')],'Values':[field('Cohorts','Cohort Retention',True)]})
visual('retention','segments','clusteredBarChart','Scored customers by behavior segment • Dec 10 snapshot',20,520,800,180,
       {'Category':[field('Customers','segment')],'Y':[field('Customers','Scored Customers',True)]})
visual('retention','customerscount','card','Customers in latest scoring population',840,520,420,180,{'Values':[field('Customers','Scored Customers',True)]})
visual('customers','segmentfilter','slicer','Audience segment',20,20,400,160,{'Values':[field('Customers','segment')]})
visual('customers','count','card','Scored customers',440,20,400,160,{'Values':[field('Customers','Scored Customers',True)]})
visual('customers','propensity','card','Mean repeat propensity • not campaign uplift',860,20,400,160,{'Values':[field('Customers','Mean Repeat Propensity',True)]})
visual('customers','queue','tableEx','Customer review queue • sort priority_rank ascending',20,200,1240,490,
       {'Values':[field('Customers',c) for c in ['priority_rank','customer_id','segment','repeat_probability','recency_days','orders_180d','gross_180d']]})
write(PBI/'RetailSignal.theme.json',{'name':'RetailSignal','dataColors':['#0D9F83','#2E5B8C','#E49B49','#B96B6B'],'background':'#F5F8F9','foreground':'#173442','tableAccent':'#0D9F83'})
(PBI/'measures.dax').write_text('\n\n'.join(f'-- Table: {t}\n{n} = {e}' for t,ms in measures.items() for n,e,_ in ms)+'\n')
print('Generated Power BI semantic model, 3 report pages, 16 visuals, theme, and DAX reference.')

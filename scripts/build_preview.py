"""Render a portable SVG overview from the checked-in analytical marts."""
from pathlib import Path
from html import escape
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
m=pd.read_csv(ROOT/'data/exports/mart_monthly.csv')
d=pd.read_csv(ROOT/'data/exports/mart_daily_country.csv')
q=json.loads((ROOT/'reports/data_quality.json').read_text())
e=json.loads((ROOT/'reports/model_evaluation.json').read_text())
parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900">']
def rect(x,y,w,h,fill,rx=12):parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>')
def text(x,y,s,size=16,color='#173442',bold=False):parts.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{escape(str(s))}</text>')
rect(0,0,1440,900,'#f5f8f9',0);rect(0,0,240,900,'#101f2e',0)
text(28,65,'◈ RetailSignal',26,'#ffffff',True)
text(28,97,'DECISION INTELLIGENCE',11,'#7fb6b5')
for i,s in enumerate(['Revenue overview','Customer retention','Decision lab','Model evidence','Data trust','Analyst desk']):
 if i==0:rect(18,132+i*49,204,39,'#244353',8)
 text(31,157+i*49,s,16,'#ffffff' if i==0 else '#c2d1d7')
text(28,680,'PUBLIC DATA CASE STUDY',11,'#77d8bd')
text(28,714,'Dec 2010 – Dec 2011',15,'#c2d1d7')
text(28,745,'Currency: GBP (£)',15,'#c2d1d7')
text(28,831,'Sree Vidya Cheekuri',15,'#ffffff')
rect(270,26,1140,158,'#102a38')
text(300,62,'RETAILSIGNAL / ANALYTICAL SNAPSHOT',12,'#6ee7c0',True)
text(300,113,'Know where value flows.',40,'#ffffff',True)
text(300,151,'A reconciled view of revenue, customer coverage, and predictive evidence.',18,'#c2d1d7')
vals=[('NET REVENUE',f"£{q['net_gbp']/1e6:.2f}M"),('GROSS REVENUE',f"£{q['gross_gbp']/1e6:.2f}M"),('CREDIT / GROSS',f"{q['credits_gbp']/q['gross_gbp']:.1%}"),('SALES ORDERS',f'{int(d.orders.sum()):,}')]
for i,(label,value) in enumerate(vals):
 x=270+i*290;rect(x,207,270,111,'#ffffff');text(x+20,240,label,12,'#627781');text(x+20,286,value,32,bold=True)
rect(270,342,704,305,'#ffffff');text(292,378,'Monthly revenue',22,bold=True)
text(292,404,'December 2011 is partial',12,'#627781')
for v in [0,500000,1000000,1500000]:
 y=600-v/1500000*165
 parts.append(f'<path d="M330 {y}H948" stroke="#eaf0f2"/>');text(284,y+4,f'{v/1e6:.1f}M',11,'#627781')
for col,color in [('gross_revenue','#0d9f83'),('net_revenue','#2e5b8c')]:
 points=' '.join(f'{335+i*50},{600-v/1500000*165:.2f}' for i,v in enumerate(m[col]))
 parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
for i,label in enumerate(['Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']):text(325+i*50,625,label,10,'#627781')
text(710,403,'Gross',12,'#0d9f83');text(790,403,'Net',12,'#2e5b8c')
rect(994,342,416,305,'#ffffff');text(1016,378,'Markets that matter',22,bold=True)
markets=d.groupby('country').net_revenue.sum().nlargest(5)
for i,(country,value) in enumerate(markets.items()):
 y=410+i*44;text(1016,y,country,13);rect(1125,y-12,max(2,value/markets.max()*205),17,'#0d9f83',3);text(1340,y,f'{value/1e6:.2f}M',11,'#627781')
rect(270,671,557,163,'#ffffff');text(292,707,'The identity gap',22,bold=True)
text(292,751,f'{d.anonymous_gross.sum()/d.gross_revenue.sum():.1%}',32,'#0d9f83',True)
text(400,750,'of gross revenue has no customer ID',16)
text(292,789,'Keep it in financial totals; exclude individual-level modeling.',14,'#627781')
rect(847,671,563,163,'#ffffff');text(869,707,'Model evidence, not promised ROI',22,bold=True)
text(869,751,f"{e['test']['lift_at_20pct']:.2f}×",32,'#2e5b8c',True)
text(985,750,'repeat-buyer lift in the highest-scored 20%',16)
text(869,789,'Temporal holdout · AP 0.554 · Recency baseline AP 0.351',14,'#627781')
text(270,869,'Generated from published project outputs. Interactive filters and review queues are available in the Streamlit app.',13,'#627781')
parts.append('</svg>')
(ROOT/'docs/assets/analytical-overview.svg').write_text('\n'.join(parts))

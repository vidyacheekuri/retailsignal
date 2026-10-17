from pathlib import Path
import json
import re
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def test_semantic_model_contracts_and_relationships():
    model=json.loads((ROOT/'powerbi/RetailSignal.SemanticModel/model.bim').read_text())['model']
    tables={t['name']:t for t in model['tables']}
    for t in tables.values():
        expression='\n'.join(t['partitions'][0]['source']['expression'])
        filename=re.search(r'DataFolder & "/([^\"]+)"',expression).group(1)
        df=pd.read_csv(ROOT/'data/exports'/filename)
        assert {c['sourceColumn'] for c in t['columns']} <= set(df.columns)
    for rel in model['relationships']:
        assert rel['fromTable'] in tables and rel['toTable'] in tables
        target=tables[rel['toTable']]
        assert rel['toColumn'] in [c['name'] for c in target['columns']]


def test_every_visual_binds_to_a_real_model_field():
    model=json.loads((ROOT/'powerbi/RetailSignal.SemanticModel/model.bim').read_text())['model']
    tables={t['name']:t for t in model['tables']}
    def walk(node):
        if isinstance(node,dict):
            for kind in ['Column','Measure']:
                if kind in node:
                    expr=node[kind]
                    table=expr['Expression']['SourceRef']['Entity']
                    key='columns' if kind=='Column' else 'measures'
                    assert expr['Property'] in [v['name'] for v in tables[table].get(key,[])]
            for v in node.values():walk(v)
        elif isinstance(node,list):
            for v in node:walk(v)
    for p in (ROOT/'powerbi/RetailSignal.Report').rglob('visual.json'):
        walk(json.loads(p.read_text()))

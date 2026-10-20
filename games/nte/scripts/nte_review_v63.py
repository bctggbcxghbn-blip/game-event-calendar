#!/usr/bin/env python3
"""V63: read-only deep review of V62 NTE candidate report. Python 3.12, stdlib only."""
import argparse,csv,json,re
from pathlib import Path

EVENT_GROUPS={
 'ガチャ・弧盤':{6:'クロバネ（新規）',7:'クロバネ（新規）',9:'罪と罰（新規弧盤）',10:'罪と罰（新規弧盤）',12:'レクイエム（復刻）',13:'レクイエム（復刻）',14:'レクイエム（復刻）',16:'ラスト・ローズ（復刻弧盤）'},
 'キャラ追加・衣装':{17:'クロバネ関連コンテンツ',18:'クロバネ関連コンテンツ',19:'クロバネ関連コンテンツ',20:'クロバネ「蒼羽ソワレ」割引',21:'クロバネ（新規）',22:'クロバネ関連コンテンツ'},
 'Porscheコラボ':{23:'Porscheコラボ（開催期間の可能性）',26:'Porscheコラボ：ファントムラン',28:'Porscheコラボ：エバードライブ（復刻）',29:'Porscheコラボ：エバードライブ（復刻）'},
 'イベント説明':{32:'7Daysボーナス',34:'プカ遊園祭',36:'極限昇段戦',38:'炭団子の秘宝',39:'炭団子の秘宝',41:'スタミナブースト',42:'スタミナブースト',44:'ピクセルオーバーフロー',45:'ピクセルオーバーフロー',46:'ピクセルオーバーフロー',54:'クロバネの招待状（Webイベント）',55:'クロバネの招待状（Webイベント）',56:'クロバネの招待状（Webイベント）',57:'クロバネの招待状（Webイベント）',58:'クロバネの招待状（Webイベント）'},
 'パス・報酬':{47:'プカプラン',48:'プカプラン',49:'ハンター補給',50:'ハンター補給',51:'ハンター補給',52:'ハンター補給'},
 '告知・更新・不具合':{0:'メンテナンス',1:'前バージョン終了告知',2:'受取条件',3:'受取条件',4:'セクション見出し',30:'セクション見出し',59:'機能追加',60:'ハンター補給',61:'機能追加',62:'クロバネ関連コンテンツ',63:'クロバネ関連コンテンツ',64:'クロバネ関連コンテンツ',65:'不具合・最適化',66:'不具合・最適化',67:'不具合・最適化',68:'不具合・最適化',69:'不具合・最適化'}
}
LOOKUP={i:(cat,name) for cat,items in EVENT_GROUPS.items() for i,name in items.items()}
DATES={23,38,41,44,54}
NEW={47,49}
COSTUME={20}

def classify(r):
 i=r['index']; category,related=LOOKUP.get(i,('未分類','未確認'))
 if i in DATES: disposition='期間証拠（対象イベントと照合）'
 elif i in NEW: disposition='新規掲載候補（開催期間の確認が必要）'
 elif i in COSTUME: disposition='要確認案件の関連証拠（割引とは未確定）'
 elif category in ('告知・更新・不具合','パス・報酬'): disposition='原則カレンダー対象外／別途確認'
 else: disposition='既存項目の補足（新規登録しない）'
 return {'index':i,'category':category,'related_event':related,'disposition':disposition,'source_text':r['source_text'],'requires_manual_review':i in DATES|NEW|COSTUME,'confidence':'要検証' if i in DATES|NEW|COSTUME else '分類のみ'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True,help='V62 report.json');p.add_argument('--output',default='nte-v63-output');a=p.parse_args()
 source=json.loads(Path(a.input).read_text(encoding='utf-8'))
 if len(source['unmatched_candidates'])!=56 or len(source['registered_items'])!=14: raise SystemExit('V62 input count mismatch; no output created')
 rows=[classify(r) for r in source['unmatched_candidates']]
 if len({r['index'] for r in rows})!=56: raise SystemExit('Duplicate candidate index')
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 issues=[{'issue':'クロバネ「蒼羽ソワレ」割引','status':'未解決','evidence_indices':[20,21,22], 'reason':'候補20は「通常価格:異晶×3280（期間限定18%OFF）」のみで、衣装名・割引開始日・終了日の直接証拠がない。候補21・22は獲得方法等であり割引の開催期間を示さない。','existing_dates':'2026-10-07〜2026-11-11（V62登録値・未検証）','next_check':'元記事の前後の見出し、ゲーム内衣装ストアの名称と割引期間を確認。証拠が揃うまで変更禁止'}, {'issue':'プカプラン／ハンター補給','status':'掲載可否と期間を要確認','evidence_indices':[47,48,49,50,51,52,60],'reason':'未一致文章に固有コンテンツの説明あり。開催期間を特定できない','next_check':'元記事の見出し・開始終了日時・イベントか常設パスかを確認'}]
 report={'version':63,'mode':'read_only_review','source':'V62 report.json','summary':{'registered':14,'matched':13,'needs_review':1,'unmatched_reviewed':len(rows),'newly_imported':0,'date_evidence_indices':sorted(DATES),'potential_new_indices':sorted(NEW)},'issues':issues,'candidates':rows,'caveats':['V61候補本文だけでは見出しと日付の正確な対応が保証されない','サーバー時間とJSTを同一視しない','既存の開始終了日を自動修正しない','イベント登録・カレンダーUI変更は行わない']}
 (out/'nte-review-v63.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 with (out/'nte-review-v63.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 md=['# NTE V63 詳細レビュー','','**変更対象：調査レポートのみ。イベント自動登録0件。**','','## 要確認：クロバネ「蒼羽ソワレ」割引','候補20に「通常価格:異晶 × 3280（期間限定18%OFF）」があるが、対象衣装の名称・期間を明示する証拠が候補にない。既存の10/7〜11/11は未検証。','','## 開催期間の証拠候補','']
 for r in rows:
  if r['index'] in DATES:md.append(f"- 候補{r['index']} → {r['related_event']}：{r['source_text']}")
 md+=['','※ 候補23・38・54はJST明記。候補41・44はサーバー時間でありJST変換未確定。','','## 新規掲載を検討する項目','- プカプラン（候補47・48）：開始・終了日時が不足','- ハンター補給（候補49〜52、60）：期間限定イベントかシーズンパスかを要確認','','## 全56件の分類','']
 for r in rows:md.append(f"- [{r['index']:02d}] {r['category']}｜{r['disposition']}｜{r['related_event']}：{r['source_text']}")
 (out/'nte-review-v63.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
 print(f'V63 completed: {len(rows)} candidates, 0 imports. Output: {out}')
if __name__=='__main__':main()

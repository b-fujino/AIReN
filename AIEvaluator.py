'''
Study_Outputフォルダ内にあるファイルの中で'AIReN', 'Guided’, 'NoGuided'のいずれかを含むファイルについて，以下の観点からLLMに評価させる．
- 含まれる情報の量
- 含まれる情報の質
'''
import json
import time

from call_openai_api_openai import Agent_chat, Agent_chat_parsed
from pydantic import BaseModel, Field

class EvalresultModel(BaseModel):
    information_amount: int = Field(description="含まれる情報の量を100点満点の整数で表したもの．")
    information_quality: int = Field(description="含まれる情報の質を100点満点の整数で表したもの．")

Evaluator = """
# あなたの役割
あなたは安全管理の専門家であり，事故情報やヒヤリハット情報を数多く目にしてきた，事故情報・ヒヤリハット情報のエキスパートです．

# あなたに提供されるデータ
Userから提供されるコンテンツは，ヒヤリハットを経験した人に対して聞き取り調査を行った結果を，所定のフォーマットに従って整理したものです．

# あなたのタスク
Userから提供されるコンテンツに対して、含まれる情報の量を100点満点の整数で表したものをinformation_amount、含まれる情報の質を100点満点の整数で表したものをinformation_qualityとして答えてください。

# 注意事項
- 標準的な評価点は50点とします．標準偏差は15点とします．
- 含まれる情報の量は，提供されたコンテンツの各項目がどれだけカバーされているかを評価してください．カバーされている項目が多ければ多いほど高い点数を与えてください．
- 含まれる情報の質は，提供されたコンテンツの中に各項目に記載の情報がどれだけ深掘りできているかを評価してください．情報が深いものであればあるほど高い点数を与えてください．
- あなたは安全管理の専門家であるため，提供されたコンテンツに対して公正で厳格な評価を行うことが期待されます．そのため，点数をつける際には慎重に評価を行ってください．
"""

def combinations_manual(items, r):
    if r == 0:
        return [[]]
    if len(items) == 0:
        return []
    
    head = items[0]
    tail = items[1:]
    
    # 最初の要素を含む組み合わせ
    with_head = [[head] + combo for combo in combinations_manual(tail, r - 1)]
    # 最初の要素を含まない組み合わせ
    without_head = combinations_manual(tail, r)
    
    return with_head + without_head

modelname = "gpt-4o"


if __name__ == "__main__":
    
    # Study_Outputフォルダ内にあるファイルの中で'AIReN', 'Guided’, 'NoGuided'のいずれかを含むファイルを取得する．
    import os
    files = os.listdir("Study_Output")
    target_files = [file for file in files if "AIReN" in file or "Guided" in file or "NoGuided" in file]

    #取得したファイルの１対比較の組み合わせを作成する．→　一対比較でリーグ戦できないか？
    combinations = combinations_manual(target_files, 2)

    for file in target_files:
        with open(f"Study_Output/{file}", "r", encoding="utf-8") as f:
            content1 = json.load(f)

        Evalresult = Agent_chat_parsed(
            system_prompt = Evaluator,
            messages = [{"role": "user", "content": json.dumps(content1, ensure_ascii=False)}],
            format=EvalresultModel,
            model=modelname,
            print_output=False
        )
        print(f"File: {file}")
        print(f"Evaluation Result: {Evalresult}\n")
        time.sleep(1) # 連続してAPIを呼び出すことによる問題を避けるために，1秒のスリープを入れる．

        #結果をcsvファイルに保存する．
        import csv
        with open("Evaluation_Results.csv", "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([file, Evalresult['information_amount'], Evalresult['information_quality']])  
    




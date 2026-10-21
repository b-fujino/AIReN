'''
Study_Outputフォルダ以下（サブフォルダを含む）にあるJSONファイルの中で，ファイル名に'AIReN', 'Guided', 'NoGuided'のいずれかを含むものについて，以下の観点からLLMに評価させる．
- 含まれる情報の量（網羅性）
- 含まれる情報の質（深さ）
- 含まれる情報の有用性（ダブルループ学習への有用性）
'''
import json
import time

from call_openai_api_Ollama import Agent_chat, Agent_chat_parsed, Agent_chat_tools, modelname
#from call_openai_api_openai import Agent_chat, Agent_chat_parsed
from pydantic import BaseModel, Field

class EvalresultModel(BaseModel):
    information_amount: int = Field(description="含まれる情報の網羅性を整数で表したもの．")
    information_quality: int = Field(description="含まれる情報について，どこまで深く聞き取れているかを整数で表したもの．")
    information_usefulness: int = Field(description="含まれる情報がダブルループ学習をする上でどの程度有用であるかを整数で表したもの．")


Evaluator = """
# あなたの役割
あなたは安全管理の専門家であり，事故情報やヒヤリハット情報を数多く目にしてきた，事故情報・ヒヤリハット情報のエキスパートです．

# あなたに提供されるデータ
Userから提供されるコンテンツは，ヒヤリハットを経験した人に対して聞き取り調査を行った結果を，所定のフォーマットに従って整理したものです．

# あなたのタスク
Userから提供されるコンテンツに対して、含まれる情報の量を100点満点の整数で表したものをinformation_amount、含まれる情報の質を100点満点の整数で表したものをinformation_quality、含まれる情報の有用性を100点満点の整数で表したものをinformation_usefulnessとして答えてください。

# 注意事項
- 標準的な評価点は50点とします．標準偏差は15点とします．
- 含まれる情報の量は，提供されたコンテンツの各項目がどれだけカバーされているかを評価してください．カバーされている項目が多ければ多いほど高い点数を与えてください．
- 含まれる情報の質は，提供されたコンテンツの中に各項目に記載の情報がどれだけ深掘りできているかを評価してください．情報が深いものであればあるほど高い点数を与えてください．
- 含まれる情報の有用性は，提供されたコンテンツに含まれる情報がダブルループ学習をする上でどの程度有用であるかを評価してください．有用性が高いほど高い点数を与えてください．
- あなたは安全管理の専門家であるため，提供されたコンテンツに対して公正で厳格な評価を行うことが期待されます．そのため，点数をつける際には慎重に評価を行ってください．
"""

#modelname = "gpt-5-mini"  # "gpt-4o" "gpt-4o-mini" "gpt-5-nano"


if __name__ == "__main__":
    
    # Study_Outputフォルダ以下のJSONファイルの中で'AIReN', 'Guided'（'NoGuided'を含む）のいずれかを含むファイルを取得する．
    # （実験スクリプトはサブフォルダに出力し，同名のチャットログ.txtも出力するため，再帰的に探索して.jsonに限定する）
    import os
    target_files = []
    for root, _, files in os.walk("Study_Output"):
        for file in files:
            if file.endswith(".json") and ("AIReN" in file or "Guided" in file):
                target_files.append(os.path.join(root, file))
    target_files.sort()

    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for file in target_files:
        with open(file, "r", encoding="utf-8") as f:
            content1 = json.load(f)

        Evalresult = Agent_chat_parsed(
            system_prompt = Evaluator,
            messages = [{"role": "user", "content": json.dumps(content1, ensure_ascii=False)}],
            format=EvalresultModel,
            #model=modelname,
            effort="high",
            print_output=False
        )
        print(f"File: {file}")
        print(f"Evaluation Result: {Evalresult}\n")
        time.sleep(1) # 連続してAPIを呼び出すことによる問題を避けるために，1秒のスリープを入れる．

        #結果をcsvファイルに保存する．
        import csv

        with open(f"Evaluation_Results_timestamp{timestamp}_{modelname}.csv", "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([file, Evalresult.information_amount, Evalresult.information_quality, Evalresult.information_usefulness])  
    




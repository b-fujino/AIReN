import json


'''
構造化出力のためのPydanticモデル
'''
from pydantic import BaseModel, Field

class CheckSimilarity(BaseModel):
    is_similar: bool = Field(description="もし意味が同じなら, true; もし意味が違っていたら, false.")



SIMILARITY_CHECKER_J = f""""
あなたは与えられた2つの文章が同じ意味を持つかどうかを判断するエキスパートです．
[1]と[2]の文章が同じ意味を持つ場合は'true'，そうでない場合は'false'と答えてください．

出力は以下のJSONスキーマに厳密に従ってJSONのみを返してください．
スキーマ: {json.dumps(CheckSimilarity.model_json_schema(), ensure_ascii=False)}

例：
{{"is_similar": false}}
{{"is_similar": true}}


"""

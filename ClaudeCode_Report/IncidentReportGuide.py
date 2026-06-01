'''
ヒヤリハット報告書の基本フォーマット．
JSONSchemaに基づいてPydanticモデルを定義する．
このモデルは，ヒヤリハット報告書の内容を構造化されたデータとして表現するためのものである．
'''


from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


# -----------------------
# 下位モデル
# -----------------------
class 報告者情報Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    名前: Optional[str] = None
    年齢: Optional[int] = None
    性別: Optional[str] = None
    職種: Optional[str] = None
    会社: Optional[str] = None
    勤続年数: Optional[int] = None


class インシデント概要Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    日付: Optional[str] = Field(default=None, description="インシデントの発生日")
    時刻: Optional[str] = Field(default=None, description="インシデントの発生時刻")
    場所: Optional[str] = Field(default=None, description="インシデントの発生場所")
    概要: Optional[str] = Field(default=None, description="起こったことの概要")


class 当人LModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    行動: Optional[str] = None
    見ていたもの: Optional[str] = None
    聴いていたこと: Optional[str] = None
    感情状態: Optional[str] = None
    認知状態: Optional[str] = None
    身体状態: Optional[str] = None
    受けていた指示: Optional[str] = None
    受け取っていた情報: Optional[str] = None


class ソフトウェアSModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    マニュアル: Optional[str] = None
    手順: Optional[str] = None
    情報: Optional[str] = Field(
        default=None,
        description="アラーム・警報・サイン・信号・表示等",
    )


class ハードウェアHModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    機械: Optional[str] = None
    設備: Optional[str] = None
    工具: Optional[str] = None
    アプリケーション: Optional[str] = None


class 物理環境EModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    温度: Optional[str] = None
    湿度: Optional[str] = None
    騒音レベル: Optional[str] = None
    明るさ: Optional[str] = None
    広さ: Optional[str] = None
    障害物: Optional[str] = None
    その他: Optional[str] = None


class 周囲の人LModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    同僚: Optional[str] = None
    上司: Optional[str] = None
    顧客: Optional[str] = None
    その他: Optional[str] = None


class インシデント発生時状況Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    当人_L: Optional[当人LModel] = Field(
        default=None,
        description="インシデント発生直前の報告者の行動、認知、感情",
    )
    ソフトウェア_S: Optional[ソフトウェアSModel] = Field(
        default=None,
        description="インシデント発生時のソフトウェア環境",
    )
    ハードウェア_H: Optional[ハードウェアHModel] = Field(
        default=None,
        description="インシデント発生時のハードウェア環境",
    )
    物理環境_E: Optional[物理環境EModel] = Field(
        default=None,
        description="インシデント発生時の物理的環境の状態",
    )
    周囲の人_L: Optional[周囲の人LModel] = Field(
        default=None,
        description="インシデント発生時の報告者の周囲の人とその行動",
    )


class 背後要因_業務Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    難易度: Optional[str] = Field(default=None, description="仕事の難易度の印象")
    責任の重さ: Optional[str] = Field(default=None, description="仕事の責任の重さの印象")
    スケジュール: Optional[str] = Field(default=None, description="仕事のスケジュールの印象")
    ワークロード: Optional[str] = Field(default=None, description="仕事の負荷の印象")
    ハードウェア環境: Optional[str] = Field(default=None, description="仕事で使用される機器の印象")
    物理的環境: Optional[str] = Field(default=None, description="仕事が行われる環境の印象")
    ストレス: Optional[str] = Field(default=None, description="仕事に関連するストレスのレベルの印象")


class 背後要因_当人心理Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    モチベーション: Optional[str] = Field(default=None, description="仕事に対する報告者のモチベーションのレベル")
    職務満足度: Optional[str] = Field(default=None, description="仕事に対する報告者の満足度のレベル")
    組織コミットメント: Optional[str] = Field(default=None, description="組織に対する報告者のコミットメントのレベル")


class 背後要因_職場Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    同僚: Optional[str] = Field(default=None, description="同僚との普段の関係")
    上司: Optional[str] = Field(default=None, description="上司との普段の関係")
    職場の雰囲気: Optional[str] = Field(default=None, description="職場の雰囲気")


class 背後要因_組織Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    訓練_研修: Optional[str] = Field(default=None, description="組織が提供するトレーニングに対する印象")
    情報共有_情報開示: Optional[str] = Field(default=None, description="組織内の情報開示の慣行に対する印象")
    リスクマネジメント: Optional[str] = Field(default=None, description="組織のリスク管理の慣行に対する印象")
    意思決定: Optional[str] = Field(default=None, description="組織の意思決定の慣行に対する印象")
    コミュニケーション: Optional[str] = Field(default=None, description="組織内の異なるレベル間のコミュニケーションの慣行に対する印象")
    経営理念_経営方針: Optional[str] = Field(default=None, description="組織の方針や哲学に対する印象")


class 背後要因Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    業務: Optional[背後要因_業務Model] = Field(default=None, description="報告者の業務そのものに対する印象")
    当人の心理: Optional[背後要因_当人心理Model] = Field(default=None, description="報告者自身に内在する要因")
    職場: Optional[背後要因_職場Model] = None
    組織: Optional[背後要因_組織Model] = None


# -----------------------
# ルートモデル（format_Report_J相当）
# -----------------------
class IncidentReport_J(BaseModel):
    model_config = ConfigDict(extra="forbid")

    報告者情報: 報告者情報Model
    インシデントの概要: インシデント概要Model
    インシデント発生時の状況: インシデント発生時状況Model
    事象に至るまでの経緯: str = Field(description="インシデントに至るまでの一連の業務中の出来事")
    背後要因: 背後要因Model = Field(description="インシデントの発生に寄与した可能性のある背景要因・背後要因")
    普段と違った点: str = Field(description="通常の状況とインシデント発生時の状況の違い")
    原因: List[str] = Field(description="報告者がインシデントの原因と考える要因")
    類似事象: List[str] = Field(description="過去に発生した類似のインシデント")
    対策: List[str] = Field(description="今後同様のインシデントを防止するために講じるべき対策")



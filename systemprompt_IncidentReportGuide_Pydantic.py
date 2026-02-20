from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

REPORT_TEMPLATE = """
# The reporter's information
    - **Name**:
    - **Age**:
    - **Gender**:
    - **Job title**:
    - **Company**:
    - **Years of service**:

# Outline of the incident:
    - **Date and time of the incident**:
    - **Location of the incident**:
    - **Overview of the incident**:

# Situation at the incident:
## Liveware (the reporter) :

## Software:

## Hardware:

## Environment:

## Liveware around the reporter (colleagues, supervisors, etc.):

# Sequence leading up to the incident:

# Background factors:

# Differences from usual situations at the time of the incident:

# Considerable causal factors: 

# Similar incidents in the past:

# Measures taken to the incident:

"""

format_Report = {
    "type": "object",
    "name": "Incident Report",
    "properties": {
        "reporter": {
            "type": "object",
            "description": "information of the reporter",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "gender": {"type": "string"},
                "job_title": {"type": "string"},
                "company": {"type": "string"},
                "years_of_service": {"type": "integer"}
            }
        },
        "overview_of_incident": {
            "type": "object",
            "description": "overview of the incident",
            "properties": {
                "date": {"type": "string", "format": "date", "description": "date of the incident"},
                "time": {"type": "string", "format": "time", "description": "time of the incident"},
                "location": {"type": "string", "description": "location of the incident"},
                "overview": {"type": "string", "description": "an overview of what happened in the incident."}
            }
        },
        "situation_at_time_of_incident": {
            "type": "object",
            "description": "situation at the moment of the incident in accordance with SHELL model of safety science",
            "properties": {
                "liveware_self": {
                    "type": "object",
                    "description": "the reporter's actions, perceptions, and emotions at the time of the incident just before or at that moment",
                    "properties": {
                        "action": {"type": "string"},
                        "visual": {"type": "string"},
                        "auditory": {"type": "string"},
                        "emotional": {"type": "string"},
                        "cognitive": {"type": "string"},
                        "physical": {"type": "string"},
                        "instructions": {"type": "string"},
                        "information": {"type": "string"}
                    }
                },
                "software": {
                    "type": "object",
                    "description": "the software environment at the time of the incident",
                    "properties": {
                        "manuals": {"type": "string"},
                        "procedures": {"type": "string"},
                        "information": {"type": "string"}
                    }
                },
                "hardware": {
                    "type": "object",
                    "description": "the hardware environment at the time of the incident",
                    "properties": {
                        "machines": {"type": "string"},
                        "equipment": {"type": "string"},
                        "tools": {"type": "string"},
                        "applications": {"type": "string"}
                    }
                },
                "environment": {
                    "type": "object",
                    "description": "the environmental conditions at the time of the incident",
                    "properties": {
                        "temperature": {"type": "string"},
                        "humidity": {"type": "string"},
                        "noise_level": {"type": "string"},
                        "brightness": {"type": "string"},
                        "spaciousness": {"type": "string"},
                        "obstacles": {"type": "string"},
                        "external_factors": {"type": "string"}
                    }
                },
                "liveware_around": {
                    "type": "object",
                    "description": "people around the reporter and their actions at the time of the incident",
                    "properties": {
                        "colleagues": {"type": "string"},
                        "supervisors": {"type": "string"},
                        "customers": {"type": "string"},
                        "others": {"type": "string"}
                    }
                }
            }
        },
        "sequence_of_events": {
            "type": "string",
            "description": "the sequence of events leading up to the incident"
        },
        "background_factors": {
            "type": "object",
            "description": "the background factors that may have contributed to the incident",
            "properties": {
                "job": {
                    "type": "object",
                    "description": "the reporter's impression to the job itself",
                    "properties": {
                        "difficulty": {"type": "string", "description": "the difficulty level of the job"},
                        "responsibility": {"type": "string", "description": "the responsibility level of the job"},
                        "schedule": {"type": "string", "description": "the schedule of the job"},
                        "workload": {"type": "string", "description": "the workload of the job"},
                        "equipments": {"type": "string", "description": "the equipments used in the job"},
                        "environments": {"type": "string", "description": "the environments in which the job is performed"},
                        "stress": {"type": "string", "description": "the stress level associated with the job"}
                    }
                },
                "self": {
                    "type": "object",
                    "description": "the reporter's personal factors that may have contributed to the incident",
                    "properties": {
                        "motivation_to_job": {"type": "string", "description": "the motivation level of the reporter towards the job"},
                        "satisfaction_to_job": {"type": "string", "description": "the satisfaction level of the reporter towards the job"},
                        "commitment_to_organization": {"type": "string", "description": "the commitment level of the reporter towards the organization"}
                    }
                },
                "workplace": {
                    "type": "object",
                    "properties": {
                        "colleagues": {"type": "string", "description": "the usual relationships with colleagues"},
                        "supervisors": {"type": "string", "description": "the usual relationships with supervisors"},
                        "workplace_atmosphere": {"type": "string", "description": "the workplace atmosphere"},
                    }
                },
                "organization": {
                    "type": "object",
                    "properties": {
                        "training": {"type": "string", "description": "impression to the training provided by the organization"},
                        "disclosure": {"type": "string", "description": "impression to the disclosure practices of the organization"},
                        "risk_management": {"type": "string", "description": "impression to the risk management practices of the organization"},
                        "decision_making": {"type": "string", "description": "impression to the decision making practices of the organization"},
                        "communication": {"type": "string", "description": "impression to the communication practices between different levels of the organization"},
                        "policy_and_philosophy": {"type": "string", "description": "impression to the policy and philosophy of the organization"}
                    }
                }
            }
        },
        "differences_from_usual": {
            "type": "string",
            "description": "the differences between the normal situation and the situation at the time of the incident"
        },
        "causal_factors": {
            "type": "array",
            "description": "the causal factors that the reporter believed led to the incident",
            "items": {
                "type": "string",
                "description": "each of the causal factors"
            }
        },
        "similar_incidents": {
            "type": "array",
            "description": "any similar incidents that have occurred in the past",
            "items": {
                "type": "string",
                "description": "each of the similar incidents"
            }
        },
        "countermeasures": {
            "type": "array",
            "description": "the countermeasures that the reporter believes should be taken to prevent similar incidents in the future",
            "items": {
                "type": "string",
                "description": "each of the countermeasures"
            }
        }
    },
    "required": [
        "reporter",
        "overview_of_incident",
        "situation_at_time_of_incident",
        "sequence_of_events",
        "background_factors",
        "differences_from_usual", 
        "causal_factors", 
        "similar_incidents", 
        "countermeasures"
    ]
}





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

DESCRIPTION = """
In the part of 'Liveware (the reporter) ', you are expected to describe such as a following points:
    - What the reporter was doing at that time
    - What the reporter was looking at at that time
    - What the reporter was listening to at that time
    - What the reporter was feeling at that time
    - What the reporter was thinking at that time
    - The mental and physical state of the reporter at that time
    - What instructions the reporter was receiving from whom at that time
    - What information the reporter was receiving from whom at that time

In the part of 'Software', you are expected to describe such as a following points:
    - How the manuals or procedures were described at that time
    - How those manuals or procedures were arranged at that time
    - What information (instructions, alarms, notices, etc.) was arranged at that time

In the part of 'Hardware', you are expected to describe such as a following points:
    - What machines, equipment, or tools were present at that time
    - How those machines, equipment, or tools were arranged at that time
    - How those machines, equipment, or tools were operating at that time
    - What state those machines, equipment, or tools were in at that time

In the part of 'Environment', you are expected to describe such as a following points:
    - What were the temperature, humidity, noise level, and brightness at that time
    - How spacious was the area, and how were obstacles arranged at that time
    - What external factors (people or objects outside the organization) were present at that time,
      and how were they moving

In the part of 'Liveware around the reporter (colleagues, supervisors, etc.)', you are expected to describe such as a following points:
    - Who were the people around the reporter at that time
    - What were those people doing at that time
    - What was the relationship between the reporter and those people
    - What information exchange was happening between the reporter and those people at that time

In the part of 'Sequence leading up to the incident', you are expected to describe such as a following points:
    - The reporter's actions from waking up in the morning until the incident occurred
    - The reporter's physical and mental condition (stress, fatigue, concerns, etc.) leading up to the incident
    - The reporter's work progress and status on the day of the incident
    - The reporter's work progress and status leading up to the incident (changes in tasks or work environment)
    - The overall work progress and status of the workplace on the day of the incident
    - The overall work progress and status of the workplace leading up to the incident

In the part of 'Background factors', you are expected to describe such as a following points:
    - The reporter's role and responsibilities in the relevant work
    - The reporter's years of experience and skills in the relevant work
    - The reporter's previous work experience
    - The usual relationship with supervisors and colleagues
    - The overall approach and policies of the workplace regarding work
    - The overall atmosphere and culture of the workplace


In the part of 'Considerable causal factors', you are expected to describe such as a following points:
    - The reporter's actions or states  that may have contributed to the incident and the reasons for those actions or states 
    - The actions or states  of others that may have contributed to the incident and the reasons for those actions or states 
    - The actions or states of the machines, equipment, or tools that may have contributed to the incident and the reasons for those actions or states
    - The actions or states  of the environment that may have contributed to the incident and the reasons for those actions or states 
    - The actions or states  of the software that may have contributed to the incident and the reasons for those actions or states 
    - The actions or states  of the workplace that may have contributed to the incident and the reasons for those actions or states 


In the part 'Similar incidents in the past' you are expected to describe such as a following points:
    - Whether the reporter has caused similar incidents before
    - Whether others have caused similar incidents before
    - If so, what those incidents were and what measures were taken

"""

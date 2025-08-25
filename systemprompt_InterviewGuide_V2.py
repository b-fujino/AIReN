import json


INTERVIEW_GUIDE = {
    "Note": "This guide is for the interview about near misses and accidents. Interviewers will be expected to ask a question step by step to the reporter in accordance with this guide. This guide describes the basic flow and some basic questions but you can add questions in each step based on the context of the conversation. For example, if there is any ambiguous point in the reporter's response, you can delve deeper into that point.",
    "Steps": [ # Array
        {
            "step": 1, 
            "title": "Introduction", 
            "description": "The aim of this step is to establish rapport with the reporter and to make them feel comfortable to talk about the near miss or accident.",
            "directions": [
                "Introduce yourself and explain the purpose of the interview first. Emphasize that neither the reporters nor anyone mentioned in the reports will be blamed or criticized, and that all personal information will be kept strictly confidential. After that, let the reporter introduce themselves, for example, their names, ages, positions, roles and their experiences in the organization. If they want some of them to be kept confidential to you, please respect their will."
            ]
        },
        {
            "step": 2, 
            "title": "Initial Question",
            "description": "The aim of this step is to grasp the overall information of the near miss or accident.",
            "directions": [
                "Ask the reporter to provide the date and time and location as first",
                "Ask the reporter to describe their'near miss' or 'incident' in their own words concretely."
            ]
        },
        {
            "step": 3, 
            "title": "Clarifying the situation at the time of the incident",
            "description": (
                "The goal of this step is to clarify the situation at the time of the near miss in detail. "
                "This steps is strongly related to the previous question, so some information may be provided in the reply to the previous question. In that case, you have to confirm the information you have already recieved and correct it if necessary."
            ),
            "substeps": [
                {
                    "substep": 1, 
                    "title": "The reporter's state just before the nearmiss or incident.",
                    # "description":(
                    #     "Ask the reporter their physical, cognitive and emotional state at that time."
                    # ),
                    "directions":[
                        "Ask the the reporter their cognitive state just before the nearmiss or incident. For example, what the reporter is looking, listening, and thinking of ",
                        "Ask the reporter their physical state just before the nearmiss or incident. For example, their fatigue level, parts that they had any pain or discomfort.",
                        "Ask the reporter their emotional state just before the nearmiss or incident. For example, whether they were feeling stressed, anxious, or calm at that time, how they feel about the job at that time.",
                        #"Ask the reporter whether any special information they had about the task, the equipment, and the situation before the incident or near miss.",
                        "Ask about the reporter's experience with the task at that time and how confident the reporter felt in his/her ability to perform it well."
                    ],
                },
                {
                    "substep": 2,
                    "title": "Related to 'Hardware'",
                    "directions": [
                        "Ask the reporter what equipment, tools (including pc applications in some case), and machines were present at that time, how they were arranged and operating, and what condition they were in."
                    ]
                },
                {
                    "substep": 3,
                    "title": "Related to 'Software'",
                    "directions": [
                        "Ask what manuals or procedures were available at that time, how they were described and organized.",
                        "Ask whether any other special information (instructions, alarms, signs, notices, etc.) was presented at that time. If so, how those were informed to the reporter."
                    ]
                },
                {
                    "substep": 4,
                    "title": "Related to the environment at that time",
                    "directions": [
                        "Ask the temperature, humidity, noise level, and brightness at that time.",
                        "Ask how spacious was the area, and how were obstacles arranged.",
                        "Ask whether unusual people or objects were present at that time. If so, how were they moving or placed?"
                    ]
                },
                {
                    "substep": 5,
                    "title": "Related to the colleagues, supervisors, customers and others around the reporter at that time",
                    "directions": [
                        "Ask who was around the reporter at that time for example, colleagues, supervisors, customers, and others. If there was anyone, what were they doing, what was their relationship with the reporter, and what information was exchanged between the reporter and those people at that time or talked about?"
                    ]
                }
            ]
        },
        {
            "step": 4, 
            "title": "Clarifying the event sequence of leading up to the incindent",
            "description": (
                "The goal of this step is to clarify the sequence of events leading up to the near miss or accident."
                "In some cases, the reporter may have told you the sequence of events roughly in the reply to the previous questions. Even in that case, you have to ask the reporter to describe the sequence of events in detail again."

            ),
            "directions": [(
                "Ask the reporter in the first place, 'Could you walk us through what you were working on that day, step by step, from the very beginning -for example, the morning or the start of the shift of the day- to the situation the incident occurred?'."
                "Don't assume that a reporter can explain the sequence of events all at once. You have to ask and clarfy each step of events composed of the event sequence one by one."
                "In each step in the sequence of events, you will ask the reporter to describe things related to reporter, equipment, tools, machines, environment, and people around the reporter. Here, you can ask the reporter, 'Please imagine the scene now you mentioned and walk through it in your mind. What can be recalled?' if the reporter seems to struggle with recalling details."
            )]
        },
        {
            "step": 5, 
            "title": "Clarifying the differences from usual situations at the time of the incident",
            "description": "The goal of this step is to clarify the differences at that time from usual situations in the sequence of events.",
            "direction": [(
                "Ask the reporter whether there were any differences from the usual situations in each step of the sequence of events. If there were any differences, ask the reporter to describe those differences in detail and why such differences occurred."
                "You have to continue to ask until the reporter says they have no further differences to add."
            )],
        },
        {
            "step": 6, 
            "title": "Clarifying the risk perception at that time",
            "description": "The goal of this step is to clarify the risk perception of the reporter at the time.",
            "directions": [
                "Ask the reporter what information or instruction about the risk have been provided to the reporter by that time?",
                "Ask how much attention did the reporter pay to the risk at that time if the reporter had already perceived it?",
                "Ask if there is a risk usually associated with the task, how does the reporter feel about that risk usually and how does the reporter deal with that risky situation?"
            ],
        },
        {
            "step": 7,
            "title": "Clarifying the desired situation at the time of the incident",
            "description": "The goal of this step is to clarify the desired situation at the time to prevent or avoid the near miss or incidents.",
            "directions": [(
                "Ask the reporter to describe the desired situation at the time of the near miss or incident. Often, because of a sense of regret or self-blame, the reporter tends to focus on what they should have done to avoid the error — for example, saying things like 'I should have checked it' or 'I should have grasped it more firmly.' Therefore, if the reporter only describes such actions, you should ask the reporter to also describe other factors, such as the desired state of the equipment and environment, and the desired behavior of the people around the reporter at that time."
            )],
        },
        {
            "step": 8,
            "title": "Clarifying the background factors",
            "description": "The goal of this step is to identify background factors that may have contributed to the near miss or incident.",
            "substeps": [
                {
                    "substep": 1,
                    "title": "related to the aspect of his/her job itself",
                    "directions": [
                        "Ask the reporter how the reporter usually feel about the difficulty of their job and the tasks they are responsible for.",
                        "Ask the reporter how heavy the reporter usually feel about the responsibilities and the pressure you are under.",
                        "Ask the reporter How much the reporter is motivated to the job and why so.",
                        "Ask how much the reporter is satisfied with the job and why so.",
                        "Ask the reporter how the reporter usually feel and think about the work schedule and workload.",
                        "Ask the reporter how the reporter usually feel and think about the workplace environment and states of equipment?"
                    ],
                },
                {
                    "substep": 2,
                    "title": "related to the aspect of organizational management",
                    "directions": [
                        "Ask the reporter how the reporter usually feel about their relationships with colleagues and supervisors?",
                        "Ask the reporter how the reporter feel about the overall workplace atmosphere?",
                        "Ask the reporter how the reporter feel about organizational management, including training, risk management, decision-making, information disclosure, communication between different levels, and organizational policies and philosophy.",
                        "Ask the reporter how satisfied they are with the organization."
                    ],
                },
            ],
        },
        {
            "step": 9,
            "title": "Clarifying the reporters thoughts about causal and contributing factors",
            "description": "The goal of this step is to identify the reporter's thoughts about the causal and contributing factors that may have led to the near miss or incident.",
            "substeps": [
                {
                    "substep": 1,
                    "title": "Asking the reporter about the causal and contributing factors",
                    "directions": [(
                        "Ask the reporter, 'What do you think were the factors that led to the near miss or incident?'"
                        "Encourage the reporter to share as many potential causal factors as they can think of."
                        "If the reporter has already suggested some causal factors, ask the reporter whether there are any other factors that haven't been mentioned yet."
                    )],
                },
            ],
        },
            {
            "step": 10,
            "title": "Closing the interview",
            "description": "You will show the reporter the summary of the interview and ask if there is anything they would like to add or correct.",
            "substeps": [
                {
                    "substep": 1,
                    "title": "Presenting the summary to the reporter",
                    "directions": [(
                        "Summarize the key points of the interview for the reporter first. Then ask the reporter if they agree with the summary or if there are any changes they would like to make."
                    )],
                },
                {
                    "substep": 2,
                    "title": "Concluding the interview",
                    "directions": [(
                        "If the reporter has no additional information to provide, Say, 'Now we will end up the interview. Thank you for your cooperation. We will use the information you provided to prevent similar near misses and incidents in the future. Your cooperation is greatly appreciated. If you have any concerns, please feel free to contact us. Have a nice day!'"
                    )],
                },
            ],
        },
    ],
}



INTERVIEW_GUIDE_J = {
    "Note": "このインタビューガイドはヒヤリハット（ニアミス）やインシデントについてのインタビュー調査のためのものです．インタビュワーはこのガイドに沿って当事者に対して1つ１つ質問していくことが期待されます．このガイドでは基本的な流れといくつかの基本的な質問が記載されていますが，各ステップで状況に応じて質問を追加しても構いません．例えば，もし当事者の回答にあいまいな点があれば，その点について深く掘り下げて質問することができます．",
    "Steps": [ # Array
        {
            "step": 1, 
            "title": "導入", 
            "description": "このステップの目的は、報告者とのラポールを築き、ヒヤリハットや事故について話しやすい環境を作ることです。",
            "directions": [
                "まず自己紹介をし、インタビューの目的を説明してください。報告内容に基づいて責められたり、批判されたりすることは一切ないこと、すべての個人情報は厳重に機密保持されることを強調してください。その後、報告者に自己紹介をしてもらってください。例えば、名前、年齢、職位、役割、組織での経験などです。ただし，報告者がこれらの情報の一部，もしくは全部を開示したくないという場合は、その意向を尊重してください。"
            ]
        },
        {
            "step": 2, 
            "title": "最初の質問",
            "description": "このステップの目的は、ヒヤリハットや事故の全体的な情報を把握することです。",
            "directions": [
                "まず、報告者に日付、時刻、場所を提供するように求めてください。",
                "次に、報告者に自分の言葉で具体的にどのような「ヒヤリハット」や「事故」が発生したのかを説明してもらってください。"
            ]
        },
        {
            "step": 3, 
            "title": "事象発生時の状況の明確化",
            "description": (
                "このステップの目的は、ヒヤリハットや事故発生時の状況を詳細に明確化することです。"
                "このステップは前の質問と強く関連しているため、前の質問への回答の中でいくつかの情報が提供される場合があります。その場合、すでに受け取った情報を確認し、必要に応じて修正する必要があります。"
            ),
            "substeps": [
                {
                    "substep": 1, 
                    "title": "事象発生直前の当人の状況.",
                    # "description":(
                    #     "Ask the reporter their physical, cognitive and emotional state at that time."
                    # ),
                    "directions":[
                        "事象が発生する直前の当人の認知状態（例えば，何を見ていたか、何を聞いていたか、何を考えていたか）を尋ねてください． ",
                        "事象が発生する直前の当人の身体的状態（例えば，疲労度、痛みや不快感のある部位）を尋ねてください。",
                        "事象が発生する直前の当人の感情状態（例えば，その時にストレスを感じていたか、不安だったか、冷静だったか、またその時の仕事に対する気持ち）を尋ねてください。",
                        #"Ask the reporter whether any special information they had about the task, the equipment, and the situation before the incident or near miss.",
                        "事象が発生する直前の当人の経験や、自信の程度について尋ねてください。"
                    ],
                },
                {
                    "substep": 2,
                    "title": "ハードウェアに関すること",
                    "directions": [
                        "事象が起こった現場にはどのような機器、ツール（場合によってはPCアプリケーションを含む）、機械が存在していたか、また，事象発生時にそれらはどのように動作していたか、またそれらの状態について尋ねてください。"
                    ]
                },
                {
                    "substep": 3,
                    "title": "ソフトウェアに関すること",
                    "directions": [
                        "事象発生場面での作業に関して，マニュアルや作業手順はあったか，あったのであれば，どのようなことが記載されていたかを尋ねてください。",
                        "事象発生時の作業に関して，特別な情報（指示、アラーム、サイン、通知など）があったかどうかを尋ねてください。もしあった場合、それらはどのようにものだったのか，またどのように当人に示されていたかを尋ねてください。"
                    ]
                },
                {
                    "substep": 4,
                    "title": "物理環境に関すること",
                    "directions": [
                        "事象発生時の作業場の温度、湿度、騒音レベル、明るさについて尋ねてください。",
                        "事象発生場面の作業エリアの広さや障害物の有無について尋ねてください。",
                        "事象発生時，その場に普段見かけない人や物体が存在していたかどうかを尋ねてください。もし存在していた場合、それらはどのように配置されていたか，どのような動きをしていたのかを尋ねてください。"
                    ]
                },
                {
                    "substep": 5,
                    "title": "その時の同僚、上司、顧客、その他の関係者に関すること",
                    "directions": [
                        "事象発生時に当人の周囲にいた人（例えば，同僚、上司、顧客、その他の関係者）について尋ねてください。もし誰かがいた場合、彼らはその時その場で何をしていたのか、当人との関係はどのようなものだったのか、その時に当人とそれらの人々の間でどのようなコミュニケーションがなされていたのかを尋ねてください。"
                    ]
                }
            ]
        },
        {
            "step": 4, 
            "title": "事象発生場面で普段と違った点の明確化",
            "description": "このステップの目的は、事象発生場面において普段と違った点を明確化することです。場合によっては、前の質問への回答の中で、報告者が事象発生場面で普段と違った点を述べていることがあります。その場合でも、報告者に改めてそれを詳細に説明してもらってください。",
            "direction": [(
                "特に事象発生場面において、普段と違った点があったかどうかを報告者に尋ねてください。もし違った点があった場合、何がどのように違っていたのかを詳しく説明してもらってください．また，なぜそのような違いが生じた原因についてもを尋ねてください。"
            )],
        },
        {
            "step": 5,
            "title": "事象発生場面に至るまでの経緯の明確化",
            "description": (
                "このステップの目的は、ヒヤリハットや事故に至るまでの経緯を明確化することです。"
                "場合によては，前の質問への回答の中で、報告者が事象発生までの経緯を大まかに説明していることがあります。その場合でも、報告者にその経緯を詳細に説明してもらってください．"

            ),
            "directions": [(
                "まず最初に「その日にあなたが取り組んでいたことを、最初から順を追って説明していただけますか？例えば、その日，起床してから，出勤し，事象が発生した状況に至るまでの状況の推移を1つ1つ思い出してください。」と尋ねてください。"
                "各ステップにおいて、当人が詳細を思い出すのに苦労しているようであれば、「今言及したシーンを想像して、それを心の中で歩き回ってみてください。何が思い出されますか？」と尋ねることができます。"
                "特に，各ステップで普段と違う点はなかったか，あったのであれば何がどのように違っていたのかを尋ねてください。"
            )]#多分，こういう相手の返答に応じて，質問パターンを展開していくような質問方法を出させるのがAIにはしんどいのかもしれない．うまくアーキテクチャを考えればできるのか？ここのアーキテクチャを考える点がポイントか．
        },

        {
            "step": 6, 
            "title": "事象発生時の当人のリスク認知の明確化",
            "description": "このステップの目的は、事象発生時の報告者のリスク認知を明確化することです。",
            "directions": [
                "報告者がその場面でのリスクを認識していたのか，いなかったのか，もしリスクがあることを認識していた場合、事象発生時にはどの程度そのリスクに注意を払っていたか，また普段，そのリスクをどのように考えていて，そのリスクに対してどのような行動をとっているのかを尋ねてください。",
                "事象発生時，その場面でのリスクに関する情報や指示が何か提供されていたか，いたのであればどのような情報や指示が，どのように提供されていたのかについて尋ねてください。",
            ],
        },
        {
            "step": 7,
            "title": "事象発生回避のために期待されている状況",
            "description": "このステップの目的は、事象発生を避けるために期待されている状況を明確化することです。",
            "directions": [(
                "事象発生を避けるために，どのような状況（当人の行動、機器や環境の状態、周囲の人々の行動，情報の提供など）が期待されていたかを報告者に尋ねてください。特に，この場面ではしばしば、後悔や自己非難の感情から、当人は「もっと確認すべきだった」「もっとしっかり状況を把握するべきだった」といった当人自身の行動に焦点を当てがちです。そのような場合には，機器や環境の状態、周囲の人々の行動，当人に与えられるべき情報などについても説明するように促してください。"
            )],
        },
        {
            "step": 8,
            "title": "背後要因",
            "description": "このステップの目的は、ヒヤリハットやインシデントの発生に関係する背後要因を明確化することです。",
            "substeps": [
                {
                    "substep": 1,
                    "title": "当人の業務に関する事柄",
                    "directions": [
                        "普段，報告者が自分の仕事や責任をどのように感じているかを尋ねてください。",
                        "普段，報告者が自分の責任やプレッシャーをどのように感じているかを尋ねてください。",
                        "普段，報告者が業務に対してどの程度モチベーションを持っているか、またその理由について尋ねてください。",
                        "普段，報告者が業務に対してどの程度満足しているか、またその理由について尋ねてください。",
                        "普段，報告者が作業プロセスや仕事のスケジュールや負荷についてどのように感じているかを尋ねてください。",
                        "普段，報告者が職場の物理環境や機器の状態についてどのように感じているかを尋ねてください。",
                        "普段，報告者が組織や部署から当人への業務に関する情報の提供についてどのように感じているかを尋ねてください。"
                    ],
                },
                {
                    "substep": 2,
                    "title": "組織の管理に関する事柄",
                    "directions": [
                        "普段の同僚や上司との人間関係についてどのように感じているかを尋ねてください。",
                        "普段の職場の全体的な雰囲気についてどのように感じているかを尋ねてください。",
                        "普段，職場で行われているのトレーニングやリスク管理、あるいは業務プロセス，部署の運営方針について，どのように感じているかを尋ねてください．",
                        "普段，組織の意思決定プロセス、情報開示、異なるレベル間のコミュニケーション、経営理念や経営方針についてどのように感じているかを尋ねてください。",
                        "普段，組織に対してどの程度コミットメントを持っているかを尋ねてください。"
                    ],
                },
            ],
        },
        {
            "step": 9,
            "title": "当人が考える事象の原因や要因の明確化",
            "description": "このステップの目的は、ヒヤリハットやインシデントの発生に関係する原因や要因として当人はどのように考えているかを明確化することです。決して，ここで述べられていることだけが原因ではないことに注意してください。あくまで，当人の認知を明確化することが目的です。",
            "substeps": [
                {
                    "substep": 1,
                    "title": "報告者に原因や要因について尋ねる",
                    "directions": [(
                        "「ヒヤリハットやインシデントの発生につながった要因は何だと思いますか？」と尋ねてください。"
                        "当人が考えられる限りの要因を共有するよう促してください。"
                        "当人がこれまでの質問の中ですでにいくつかの要因を挙げている場合は、改めてそれらを提示するとともに，言及されていない要因が他にあるかどうかを尋ねてください。"
                    )],
                },
            ],
        },
            {
            "step": 10,
            "title": "インタビューの締めくくり",
            "description": "インタビューの要約を報告者に示し、追加や修正したい点がないかを尋ねます。",
            "substeps": [
                {
                    "substep": 1,
                    "title": "報告者への要約の提示",
                    "directions": [(
                        "インタビューの要点を報告者に要約して伝えてください。その後、報告者に要約に同意するか、変更したい点があるかを尋ねてください。"
                    )],
                },
                {
                    "substep": 2,
                    "title": "インタビューの締めくくり",
                    "directions": [(
                        "報告者が追加の情報を提供することがない場合は、「これでインタビューを終了します。ご協力ありがとうございました。今後、同様のヒヤリハットやインシデントを防ぐために、提供していただいた情報を活用させていただきます。ご協力に感謝いたします。何か懸念がある場合は、お気軽にお問い合わせください。ご安全に！」と言ってください。"
                    )],
                },
            ],
        },
    ],
}


if __name__ == "__main__":
    # INTERVIEW_GUIDEを一つひとつのステップごとに表示する
    directions = []
    for step in INTERVIEW_GUIDE["Steps"]:
        if "directions" in step:
            i = 0
            for direction in step["directions"]:
                direction = {
                    "step": step["step"],
                    "title": step["title"],
                    "description": step["description"],
                    "No.": i,
                    "direction": direction
                }
                directions.append(direction)
                i += 1
        if "substeps" in step:
            i = 0
            for substep in step["substeps"]:
                i = 0
                for direction in substep["directions"]:
                    direction = {
                        "step": step["step"],
                        "title": step["title"],
                        "substep": substep["substep"],
                        "subtitle": substep["title"],
                        # "subdescription": substep["description"],
                        "No.": i,
                        "direction": direction
                    }
                    directions.append(direction)
                    i += 1


    for direction in directions:
        print(direction)
        print("\n")


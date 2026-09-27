EXHIBITS = {
    "silk-plain-straight": "直裾素纱单衣",
    "silk-painted-robe": "印花敷彩纱丝绵袍",
}


def audience_prompt(audience: str | None, exhibit_id: str | None = None) -> str:
    if audience == "child":
        prompt = (
            "当前是湘遇儿童模式，面向6～9岁，由纸页精灵阿帛讲解。"
            "用短句和日常比喻解释术语，每次围绕一个重点，最后可给一个简短观察问题。"
            "不要考年份、训斥、索取姓名学校等个人信息；不引导模仿危险动作或历史医疗方法。"
        )
    elif audience == "adult":
        prompt = (
            "当前是湘遇成人模式。以文物、历史与文化联系组织讲解，"
            "区分事实、解释与争议，必要时解释专业术语，避免儿童化口吻。"
        )
    else:
        return ""
    prompt += "模式只改变表达，不改变证据标准；保留引用与资料不足提示，故事不能冒充事实。"
    if exhibit_id in EXHIBITS:
        prompt += f"当前页面文物为{EXHIBITS[exhibit_id]}；仅用于解析指代，具体事实仍须检索核验。"
    return prompt

_INDUSTRY_DEFAULTS = {
    "白酒": 0.10,
    "消费": 0.09,
    "科技": 0.12,
    "医药": 0.10,
    "金融": 0.10,
    "能源": 0.11,
    "制造": 0.10,
}

_GENERAL_DEFAULT = 0.10


def capm(rf, beta, erp=0.06):
    return round(rf + beta * erp, 4)


def default_industry(industry):
    return _INDUSTRY_DEFAULTS.get(industry, _GENERAL_DEFAULT)

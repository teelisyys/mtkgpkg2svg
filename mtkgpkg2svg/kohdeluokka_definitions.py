from typing import List, Tuple

KohdeluokkaSpecTuple = (
    Tuple[str, int]
    | Tuple[str, int, str]
    | Tuple[str, int, int, str]
    | Tuple[str, int, int, str, str]
)


topographic_map: List[KohdeluokkaSpecTuple] = [
    ("meri", 1),
    ("jarvi", 1),
    ("virtavesialue", 1),
    ("virtavesikapea", 1),
    ("kallioalue", 1),
    ("korkeuskayra", 1),
    # ("rakennusreunaviiva", 1),
    ("rakennus", 1),
    ("suo", 1, 35411, "suo_helppo_avoin"),
    ("suo", 1, 35412, "suo_helppo_metsa"),
    ("suo", 1, 35421, "suo_vaikea_avoin"),
    ("suo", 1, 35422, "suo_vaikea_metsa"),
    ("soistuma", 1),
    ("jyrkanne", 1),
    ("kalliohalkeama", 1),
    ("tieviiva", 1, 12316, "ajopolku"),
    ("tieviiva", 1, 12314, "kavelyjapyoratie"),
    ("tieviiva", 1, 12313, "polku"),
    ("tieviiva", 1, 12312, "talvitie"),
    ("tieviiva", 1, 12141, "ajotie"),
    ("tieviiva", 2, 12132, "autotie_IIIb"),
    ("tieviiva", 2, 12131, "autotie_IIIa"),
    ("tieviiva", 2, 12122, "autotie_IIb"),
    ("tieviiva", 2, 12121, "autotie_IIa"),
    ("tieviiva", 2, 12112, "autotie_Ib"),
    ("tieviiva", 2, 12111, "autotie_Ia"),
    ("rautatie", 2),
    ("aita", 2),
    ("kivi", 1, "p_kivi"),
    ("lahde", 1, "p_lahde"),
    ("metsamaankasvillisuus", 1, 32710, "havupuu", "p_havupuu"),
    ("metsamaankasvillisuus", 1, 32714, "sekapuu", "p_sekapuu"),
    ("metsamaankasvillisuus", 1, 32713, "lehtipuu", "p_lehtipuu"),
    # ("metsamaankasvillisuus", 1, 32715, "varvikko", "p_varvikko"),
    ("metsamaankasvillisuus", 1, 32719, "pensaikko", "p_pensaikko"),
    ("sahkolinja", 1),
    ("luonnonsuojelualue", 1),
    ("kansallispuisto", 1),
    ("puisto", 1),
    ("maatalousmaa", 1),
    # ("kunta", 1),
]

overview_map: List[KohdeluokkaSpecTuple] = [
    ("kunnanhallintoraja", 1),
    ("meri", 1),
    # ("jarvi", 1),
    # ("virtavesialue", 1),
    # ("virtavesikapea", 1),
    # ("rakennus", 1),
    # ("tieviiva", 1, 12316, "ajopolku"),
    # ("tieviiva", 1, 12314, "kavelyjapyoratie"),
    # ("tieviiva", 1, 12313, "polku"),
    # ("tieviiva", 1, 12312, "talvitie"),
    # ("tieviiva", 1, 12141, "ajotie"),
    # ("tieviiva", 1, 12132, "autotie_IIIb"),
    # ("tieviiva", 1, 12131, "autotie_IIIa"),
    # ("tieviiva", 1, 12122, "autotie_IIb"),
    # ("tieviiva", 1, 12121, "autotie_IIa"),
    # ("tieviiva", 1, 12112, "autotie_Ib"),
    # ("tieviiva", 1, 12111, "autotie_Ia"),
    ("rautatie", 1),
]

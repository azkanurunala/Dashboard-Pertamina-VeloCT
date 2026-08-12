import os
import re
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from helpers.scraping_helper import call_with_hard_timeout
from helpers.storage_backend import storage
from news.bisnis_indonesia import main_bisnis_indonesia
from news.bloomberg_technoz import main_bloomberg_technoz
from news.bank_indonesia import main_bank_indonesia
from news.bank_indonesia import close_driver as close_bank_indonesia_driver
from news.bps import main_bps
from news.cnbc import main_google_news_cnbc
from news.cnbc_id import main_cnbc
from news.cnbc_id import close_driver as close_cnbc_driver
from news.cnn import main_google_news_cnn
from news.kompas import main_kompas
from news.kontan import scrape_kontan
from news.kontan_bbm import scrape_kontan_bbm
from news.kontan_biodiesel import scrape_kontan_biodiesel
from news.oilprice import scrape_oilprice
from news.spglobal_news import scrape_spglobal
from news.tempo import scrape_tempo


# KEYWORD SYNONYMS

SINONIM_DICT: dict[str, list[str]] = {
    # ### Makroekonomi ###
    "indeks risiko geopolitik ": ["tekanan geopolitik ", "geopolitik "],
    "indeks volatilitas ": ["volatilitas "],
    "kurs ": ["nilai tukar rupiah ", "dolar ", "kurs rupiah ", "kurs dolar "],
    "ihsg ": ["pasar saham "],
    "inflasi ": [],
    "bi rate ": ["suku bunga ", "bunga bi "],
    "indonia ": [],
    "indeks sales retail ": ["indeks penjualan ritel ", "indeks ritel ", "indeks penjualan retail ", "indeks retail ", "survei penjualan eceran "],
    "indeks kepercayaan konsumen ": ["indeks kepercayaan pelanggan ", "ekspektasi konsumen ", "indeks keyakinan konsumen ", "survei konsumen bi ", "keyakinan konsumen "],
    "indeks kinerja manufaktur ": ["kinerja manufaktur ", "pmi manufaktur ", "pmi indonesia "],
    "indeks kinerja jasa ": ["kinerja jasa ", "pmi jasa ", "pmi sektor jasa "],
    "neraca perdagangan ": ["trade balance ", "neraca dagang "],
    "pertumbuhan domestik bruto ": ["PDB ", "pertumbuhan ekonomi ", "produk domestik bruto "],

    # ### Hulu Migas ###
    "harga minyak ": [
        "minyak mentah ", "harga minyak mentah ", "icp ", "wti ", "brent ", "dubai crude price ", "dated brent ",
    ],
    "volume minyak ": [
        "volume bbm ", "minyak mentah ", "lifting minyak ", "produksi minyak ", "impor minyak mentah ",
    ],

    # ### Produk Kilang Pertamina ###
    "harga produk kilang pertamina ": [
        "bbm ", "harga kilang pertamina ", "kilang pertamina ", "kilang ", "refinery ", "harga pertamina ",
        "harga bbm pertamina ", "harga pertamax ", "harga pertalite ", "harga solar ", "harga avtur ", "rdmp ",
        "harga bensin ", "harga gasoline ", "harga diesel ",
    ],
    "volume produk kilang pertamina ": [
        "bbm ", "volume kilang pertamina ", "volume kilang ", "refinery ", "volume pertamina ",
        "kilang pertamina ", "produksi bbm ", "rdmp ", "kapasitas kilang ", "kilang balikpapan ", "kilang tuban ", "impor bbm ",
        "bbm pertamina ", "pertamax ", "pertalite ", "solar ", "avtur ", "produksi kilang ",
    ],
    "RON 92 ": [
        "pertamax ", "RON 95 ", "RON 97 ", "Residual FO ", "Fuel Oil", "Jet Fuel ", "Avtur ",
        "Kerosene ", "refinery ", "refined products ", "refining ", "oil products ", "Gasoline ",
        "Heavy Oil ", "Diesel ", "Gasoil ", "Naphtha ", "LPG ", "Biodiesel ", "Biogasoline ",
        "Petroleum Coke ", "Oil price ", "fuel cost ", "fuel price ",
    ],

    # ### Petrokimia Hulu ###
    "Petrochemical ": [
        "chemical ", "aromatic ", "olefin ", "polymer ", "LPG ",
        "Paraxylene ", "Propylene ", "Benzene ", "Green Coke ",
        "petrochemicals ", "petrokimia ", "petrochemical complex ",
        "aromatic compound ", "BTX aromatic ", "senyawa aromatik ",
        "green petroleum coke ", "petroleum coke ", "polyethylene",
        "polypropylene", "etilena", "propilena",
    ],

    # ### Bioenergi ###
    "biodiesel ": [
        "minyak kelapa sawit ", "crude palm oil ", "CPO ", "minyak sawit ", "kelapa sawit ", "sawit ",
        "HIP BBN Biodesel ", "biodiesel ", "harga fame ", "harga indeks pasar biodiesel ", "b40 ", "b50 ", "biodiesel ", "biofuel ",
    ],
    "SAF ": [
        "UCO ", "CORSIA ", "SAFCo ", "biorefinery ", "minyak jelantah ", "bioavtur ",
        "bioavtur pertamina", "pome",
    ],
    "bioetanol ": [
        "tebu ", "gula ", "molase ", "etanol ", "ethanol ", "bioethanol ", "tetes tebu ",
        "gula tebu ", "industri gula ",
    ],

    ### Ketenagalistrikan, energi baru dan terbarukan ###
    "RUPTL ": [
        "PLN ", "IPP ", "PJBL ", "ketenagalistrikan ",
        "batubara ", "batu bara ", "panas bumi ", "surya ", "nuklir ",
        "BESS ", "PLTA ", "PLTAL ", "PLTB ", "PLTBg ", "PLTBm ", "PLTD ", "PLTG ",
        "PLTGU ", "PLTM ", "PLTMG ", "PLTN ", "PLTP ", "PLTS ", "PLTSa ", "PLTU ",
        "transmisi listrik ", "transmisi tenaga listrik ",
        "panel surya ", "energi surya ", "tenaga surya ",
    ],
    "LCOE ": [
        "harga jual listrik EBT ", "harga listrik EBT ",
        "PLTA ", "PLTS ", "PLTB ", "BESS ", "PLTBm ", "panas bumi ",
        "PLTP ", "PLTBg ", "PLN ", "IPP ", "PJBL ",
    ],
    "WTE ": [
        "waste to energy ", "sampah ", "sampah jadi listrik ",
        "sampah jadi energi ", "insinerator ", "PSEL "
    ],
    "Pembangkit listrik nuklir ": [
        "PLTN ", "pembangkit nuklir ", "reaktor nuklir ",
        "energi nuklir ", "nuklir ",
    ],
}


# EXCLUDE & FILTER RULES

# --- Global exclude: berlaku untuk semua keyword ---
GLOBAL_EXCLUDE_KEYWORDS: list[str] = [
    # Institusi hukum
    "kejagung", "kejaksaan agung", "jaksa agung",
    "mahkamah agung", "kpk",
    # Status hukum
    "tersangka", "terdakwa", "terpidana",
    "korupsi", "kolusi", "nepotisme", "kkn",
    # Proses hukum
    "persidangan",
    "sidang tipikor", "sidang korupsi", "sidang perdana",
    "sidang vonis", "sidang tuntutan", "sidang dakwaan", "sidang pledoi",
    # Pelaku/saksi
    "saksi",
]

_ENERGI_TERMS: list[str] = [
    "pembangkit", "transmisi", "ruptl", "energi listrik", "gardu", "pasokan listrik",
]
_ENERGI_EBT_TERMS: list[str] = [
    "ebt", "energi terbarukan", "energi baru terbarukan", "energi berkelanjutan",
]
_SAMPAH_TERMS: list[str] = [
    "psel", "wte", "waste to energy", "energi listrik", "pltsa", "insinerator",
]
_NUKLIR_ENERGI_TERMS: list[str] = _ENERGI_TERMS + ["pembangkit ", "energi "]
_BBM_REQUIRED: list[str] = [
    # Produk BBM spesifik
    "pertamax", "pertalite", "dexlite", "biosolar",
    "solar subsidi", "avtur", "spbu",
    # Isu substantif
    "harga bbm", "bbm subsidi", "bbm nonsubsidi",
    "impor bbm", "ekspor bbm", "stok bbm",
    # Aktor utama
    "pertamina", "kilang", "esdm", "lifting",
    "bph migas", "patra niaga",
    # Dampak langsung
    "nelayan", "ojol", "logistik",
    # Kebijakan
    "subsidi", "nonsubsidi", "kompensasi energi",
]
_RDMP_REQUIRED: list[str] = [
    "kilang", "refinery", "kapasitas", "produksi",
    "konstruksi", "pembangunan", "rampung", "progress",
    "investasi", "onstream", "commissioning",
    "throughput", "barel", "revamping",
]
_AVTUR_KILANG_REQUIRED: list[str] = [
    "kilang", "produksi", "refinery", "kapasitas",
    "lifting", "barel", "pasokan avtur",
    "harga avtur", "impor avtur", "kargo avtur",
]
_PERTAMAX_KILANG_REQUIRED: list[str] = [
    "kilang", "produksi", "refinery", "kapasitas",
    "lifting", "barel", "impor", "harga pertamax",
    "ron", "oktan", "spbu", "pertamina",
]
_SOLAR_KILANG_REQUIRED: list[str] = [
    "kilang", "produksi", "refinery", "kapasitas",
    "lifting", "barel", "impor", "harga solar",
    "biosolar", "dexlite", "gasoil", "spbu", "pertamina",
]
_NERACA_TERMS: list[str] = [
    # Frasa inti neraca
    "neraca perdagangan", "trade balance", "neraca dagang",
    "surplus perdagangan", "defisit perdagangan",
    "surplus neraca", "defisit neraca",
    # Statistik agregat ekspor/impor Indonesia
    "ekspor nonmigas", "impor nonmigas",
    "ekspor migas", "impor migas",
    "neraca migas", "neraca nonmigas",
    # Konteks laporan BPS spesifik perdagangan
    "bps catat ekspor", "bps catat impor",
    "bps rilis ekspor", "bps rilis impor",
    "data perdagangan indonesia",
    # Ekspor/impor Indonesia sebagai topik utama
    "ekspor ri", "impor ri",
    "ekspor indonesia", "impor indonesia",
]

# --- Post-filter: artikel harus mengandung salah satu term (include filter) ---
POST_FILTER_RULES: dict[str, dict[str, list[str]]] = {

    # --- RUPTL / PLN ---
    "RUPTL ": {
        # "RUPTL ": tidak pakai filter
        "PLN ":                    _ENERGI_TERMS,
        "IPP ":                    _ENERGI_TERMS,
        "PJBL ":                   _ENERGI_TERMS,
        "ketenagalistrikan ":      _ENERGI_TERMS,
        "surya ":                  _ENERGI_TERMS,
        "nuklir ":                 _ENERGI_TERMS,
        "BESS ":                   _ENERGI_TERMS,
        "PLTA ":                   _ENERGI_TERMS,
        "PLTAL ":                  _ENERGI_TERMS,
        "PLTB ":                   _ENERGI_TERMS,
        "PLTBg ":                  _ENERGI_TERMS,
        "PLTBm ":                  _ENERGI_TERMS,
        "PLTD ":                   _ENERGI_TERMS,
        "PLTG ":                   _ENERGI_TERMS,
        "PLTGU ":                  _ENERGI_TERMS,
        "PLTM ":                   _ENERGI_TERMS,
        "PLTMG ":                  _ENERGI_TERMS,
        "PLTN ":                   _ENERGI_TERMS,
        "PLTP ":                   _ENERGI_TERMS,
        "PLTS ":                   _ENERGI_TERMS,
        "PLTSa ":                  _ENERGI_TERMS,
        "PLTU ":                   _ENERGI_TERMS,
        "transmisi listrik ":      _ENERGI_TERMS,
        "transmisi tenaga listrik ":_ENERGI_TERMS,
        "panel surya ":            _ENERGI_TERMS,
        "energi surya ":           _ENERGI_TERMS,
        "tenaga surya ":           _ENERGI_TERMS,
        "batubara ":               _ENERGI_TERMS + ["pltu", "dmo"],
        "batu bara ":              _ENERGI_TERMS + ["pltu", "dmo"],
        "panas bumi ":             _ENERGI_TERMS + ["pltp"],
    },

    # --- Harga & Kapasitas EBT ---
    "LCOE ": {
        # "harga jual listrik EBT ", "harga listrik EBT ": tidak pakai filter
        "PLTA ":          _ENERGI_TERMS,
        "PLTS ":          _ENERGI_TERMS,
        "PLTB ":          _ENERGI_TERMS,
        "BESS ":          _ENERGI_TERMS,
        "PLTBm ":         _ENERGI_TERMS,
        "panas bumi ":    _ENERGI_TERMS,
        "PLTP ":          _ENERGI_TERMS,
        "PLTBg ":         _ENERGI_TERMS,
        "PLN ":           _ENERGI_EBT_TERMS,
        "IPP ":           _ENERGI_TERMS,
        "PJBL ":          _ENERGI_TERMS,
        "ketenagalistrikan ": _ENERGI_TERMS,
    },

    # --- WTE ---
    "WTE ": {
        # "WTE ", "waste to energy ", "sampah jadi listrik ", "sampah jadi energi ",
        # "insinerator ", "PSEL ": tidak pakai filter
        "sampah ": _SAMPAH_TERMS,
    },

    # --- Nuklir ---
    "Pembangkit listrik nuklir ": {
        # "Pembangkit listrik nuklir ", "pembangkit nuklir ",
        # "reaktor nuklir ", "energi nuklir ": tidak pakai filter
        "PLTN ":   _NUKLIR_ENERGI_TERMS,
        # "nuklir ": tidak pakai include filter (hanya pakai exclude)
    },
    
    "biodiesel ": {
        "sawit ": [
            "biodiesel", "biofuel", "b40", "b50", "b30",
            "fame", "bahan bakar nabati", "bbn",
        ],
        "kelapa sawit ": [
            "biodiesel", "biofuel", "b40", "b50", "b30",
            "fame", "bahan bakar nabati", "bbn",
        ],
        "minyak kelapa sawit ": [
            "biodiesel", "biofuel", "b40", "b50",
            "fame", "bahan bakar",
        ],
        "CPO ": [
            "biodiesel", "biofuel", "b40", "b50", "b30",
            "fame", "bahan bakar nabati", "bbn",
            "harga cpo", "ekspor cpo",
        ],
        "crude palm oil ": [
            "biodiesel", "biofuel", "b40", "b50", "b30",
            "fame", "bahan bakar nabati", "bbn",
        ],
    },

    # --- Bioetanol (existing, tidak berubah) ---
    "bioetanol ": {
        "tebu ": [
            "etanol", "bioetanol", "biofuel", "e10", "e5", "e20",
            "molase", "bioenergi", "bahan bakar", "bbm",
        ],
        "gula ": [
            "etanol", "bioetanol", "biofuel", "e10", "e5", "e20",
            "molase", "bahan bakar",
        ],
        "gula tebu ": [
            "etanol", "bioetanol", "biofuel", "e10", "e5", "e20",
            "molase", "bahan bakar",
        ],
        "industri gula ": [
            "etanol", "bioetanol", "biofuel", "e10", "e5", "e20",
            "molase", "bahan bakar",
        ],
    },
    "harga produk kilang pertamina ": {
        "bbm ":                    _BBM_REQUIRED,
        "harga kilang pertamina ": _BBM_REQUIRED,
        "kilang pertamina ":       _BBM_REQUIRED,
        "kilang ":                 _BBM_REQUIRED,
        "refinery ":               _BBM_REQUIRED,
        "harga pertamina ":        _BBM_REQUIRED,
        "harga bbm pertamina ":    _BBM_REQUIRED,
        "harga pertamax ":         _BBM_REQUIRED,
        "harga pertalite ":        _BBM_REQUIRED,
        "harga solar ":            _BBM_REQUIRED,
        "harga avtur ":            _BBM_REQUIRED,
        "harga bensin ":           _BBM_REQUIRED,
        "harga gasoline ":         _BBM_REQUIRED,
        "harga diesel ":           _BBM_REQUIRED,
        "rdmp ":                   _RDMP_REQUIRED,
    },
    "volume produk kilang pertamina ": {
        "bbm ":                  _BBM_REQUIRED,
        "volume kilang pertamina ": _BBM_REQUIRED,
        "volume kilang ":        _BBM_REQUIRED,
        "refinery ":             _BBM_REQUIRED,
        "volume pertamina ":     _BBM_REQUIRED,
        "kilang pertamina ":     _BBM_REQUIRED,
        "produksi bbm ":         _BBM_REQUIRED,
        "bbm pertamina ":        _BBM_REQUIRED,
        "impor bbm ":            _BBM_REQUIRED,
        "kapasitas kilang ":     _BBM_REQUIRED,
        "kilang balikpapan ":    _BBM_REQUIRED,
        "kilang tuban ":         _BBM_REQUIRED,
        "produksi kilang ":      _BBM_REQUIRED,
        "rdmp ":                 _RDMP_REQUIRED,
        "avtur ":                _AVTUR_KILANG_REQUIRED,
        "pertamax ":             _PERTAMAX_KILANG_REQUIRED,
        "pertalite ":            _PERTAMAX_KILANG_REQUIRED,
        "solar ":                _SOLAR_KILANG_REQUIRED,
    },
}

CNBC_RELEVANCE_RULES: dict[str, list[str]] = {
    # --- Kurs ---
    # "rupiah", "dolar", "usd", "idr" terlalu umum — muncul di hampir semua artikel ekonomi
    "kurs ": [
        "kurs", "nilai tukar",
        "rupiah melemah", "rupiah menguat", "rupiah anjlok", "rupiah terbang",
        "dolar as", "usd/idr", "idr/usd", "devisa", "forex",
    ],
    "nilai tukar rupiah ": [
        "kurs", "nilai tukar",
        "rupiah melemah", "rupiah menguat", "rupiah anjlok",
        "dolar as", "usd/idr", "devisa",
    ],
    "dolar ": [
        "kurs", "nilai tukar",
        "rupiah melemah", "rupiah menguat",
        "dolar as", "usd/idr", "devisa", "forex",
    ],
    "kurs rupiah ": [
        "kurs", "nilai tukar", "usd/idr",
        "rupiah melemah", "rupiah menguat",
    ],
    "kurs dolar ": [
        "kurs", "nilai tukar", "usd/idr",
        "rupiah melemah", "rupiah menguat",
    ],

    # --- IHSG ---
    # "saham" terlalu umum — ganti dengan konteks pergerakan indeks
    "ihsg ": [
        "ihsg", "indeks harga saham gabungan", "bursa efek indonesia", "bei",
        "composite index", "jci",
        "ihsg menguat", "ihsg melemah", "ihsg naik", "ihsg turun",
        "ihsg ditutup", "ihsg dibuka", "ihsg anjlok", "ihsg terbang",
    ],
    "pasar saham ": [
        "ihsg", "indeks harga saham gabungan", "bursa efek indonesia", "bei",
        "composite index", "pasar modal",
        "ihsg menguat", "ihsg melemah", "ihsg naik", "ihsg turun",
    ],

    # --- Inflasi ---
    # "bps", "kenaikan harga" terlalu umum
    "inflasi ": [
        "inflasi", "deflasi",
        "indeks harga konsumen", "ihk",
        "cpi indonesia", "tingkat inflasi", "laju inflasi",
        "inflasi bulanan", "inflasi tahunan",
        "inflasi year on year", "inflasi month to month",
        "bps catat inflasi", "bps rilis inflasi",
    ],

    # --- BI Rate ---
    # "suku bunga", "bank indonesia" terlalu umum — muncul di banyak konteks
    "bi rate ": [
        "bi rate", "suku bunga acuan", "bunga acuan bank indonesia",
        "rapat dewan gubernur", "rdg bank indonesia",
        "kebijakan moneter bank indonesia",
        "bi 7-day", "bi7drrr", "repo rate bi",
    ],
    "suku bunga ": [
        "bi rate", "suku bunga acuan", "bunga acuan bank indonesia",
        "rapat dewan gubernur", "rdg bank indonesia",
        "kebijakan moneter bank indonesia", "bi 7-day",
    ],
    "bunga bi ": [
        "bi rate", "suku bunga acuan", "bunga acuan bank indonesia",
        "rapat dewan gubernur", "kebijakan moneter bank indonesia",
    ],

    # --- IndONIA --- tidak perlu filter, keyword sangat spesifik
    "indonia ": [
        "indonia", "overnight index average", "pasar uang antar bank",
        "puab", "suku bunga semalam",
    ],

    # --- Indeks Penjualan Ritel ---
    # "konsumsi", "ritel", "spe" terlalu umum
    "indeks sales retail ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "retail sales index",
        "penjualan ritel indonesia",
    ],
    "indeks penjualan ritel ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "penjualan ritel indonesia",
    ],
    "indeks ritel ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "penjualan ritel indonesia",
    ],
    "indeks penjualan retail ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "retail sales index",
    ],
    "indeks retail ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "retail sales index",
    ],
    "survei penjualan eceran ": [
        "survei penjualan eceran", "spe bank indonesia",
        "indeks penjualan ritel", "penjualan ritel indonesia",
    ],

    # --- Indeks Kepercayaan Konsumen --- tidak perlu perubahan, sudah spesifik
    "indeks kepercayaan konsumen ": [
        "indeks keyakinan konsumen", "ikk", "indeks kepercayaan konsumen",
        "survei konsumen bank indonesia", "consumer confidence index",
        "keyakinan konsumen meningkat", "keyakinan konsumen turun",
    ],
    "indeks kepercayaan pelanggan ": [
        "indeks keyakinan konsumen", "ikk",
        "survei konsumen bank indonesia", "consumer confidence index",
    ],
    "ekspektasi konsumen ": [
        "indeks keyakinan konsumen", "ikk", "ekspektasi konsumen",
        "survei konsumen bank indonesia",
    ],
    "indeks keyakinan konsumen ": [
        "indeks keyakinan konsumen", "ikk",
        "survei konsumen bank indonesia", "consumer confidence index",
    ],
    "survei konsumen bi ": [
        "survei konsumen bank indonesia", "indeks keyakinan konsumen",
        "ikk", "consumer confidence",
    ],
    "keyakinan konsumen ": [
        "indeks keyakinan konsumen", "ikk",
        "survei konsumen bank indonesia",
    ],

    # --- Indeks Kinerja Manufaktur --- tidak perlu perubahan
    "indeks kinerja manufaktur ": [
        "pmi manufaktur", "purchasing managers index manufaktur",
        "indeks kinerja manufaktur", "s&p global pmi",
        "pmi indonesia manufaktur", "aktivitas manufaktur",
    ],
    "kinerja manufaktur ": [
        "pmi manufaktur", "indeks kinerja manufaktur",
        "s&p global pmi", "aktivitas manufaktur indonesia",
    ],
    "pmi manufaktur ": [
        "pmi manufaktur", "purchasing managers index",
        "s&p global pmi", "indeks kinerja manufaktur",
    ],
    "pmi indonesia ": [
        "pmi manufaktur indonesia", "pmi jasa indonesia",
        "purchasing managers index indonesia", "s&p global pmi indonesia",
    ],

    # --- Indeks Kinerja Jasa --- tidak perlu perubahan
    "indeks kinerja jasa ": [
        "pmi jasa", "purchasing managers index jasa",
        "indeks kinerja jasa", "s&p global pmi jasa",
        "aktivitas jasa",
    ],
    "kinerja jasa ": [
        "pmi jasa", "indeks kinerja jasa",
        "s&p global pmi", "aktivitas jasa indonesia",
    ],
    "pmi jasa ": [
        "pmi jasa", "purchasing managers index jasa",
        "s&p global pmi jasa", "indeks kinerja jasa",
    ],
    "pmi sektor jasa ": [
        "pmi jasa", "pmi sektor jasa",
        "purchasing managers index jasa", "s&p global pmi",
    ],

    # --- Neraca Perdagangan ---
    "neraca perdagangan ": _NERACA_TERMS,
    "trade balance ":      _NERACA_TERMS,
    "neraca dagang ":      _NERACA_TERMS,

    # --- Pertumbuhan Ekonomi / PDB ---
    # "bps", "kuartal", "triwulan" terlalu umum
    "pertumbuhan domestik bruto ": [
        "produk domestik bruto", "pdb indonesia", "gdp indonesia",
        "pertumbuhan ekonomi indonesia", "pertumbuhan pdb",
        "ekonomi indonesia tumbuh", "kontraksi ekonomi",
        "bps catat pertumbuhan", "pdb kuartal", "gdp kuartal",
    ],
    "pdb ": [
        "produk domestik bruto", "pdb indonesia", "gdp indonesia",
        "pertumbuhan pdb", "pdb kuartal", "gdp kuartal",
        "bps catat pertumbuhan",
    ],
    "pertumbuhan ekonomi ": [
        "pertumbuhan ekonomi indonesia", "pdb indonesia", "gdp indonesia",
        "ekonomi indonesia tumbuh", "kontraksi ekonomi",
        "pertumbuhan pdb", "bps catat pertumbuhan",
    ],
    "produk domestik bruto ": [
        "produk domestik bruto", "pdb indonesia", "gdp indonesia",
        "pertumbuhan pdb", "pdb kuartal", "gdp kuartal",
    ],
}

# --- Post-sinonim-exclude: exclude per kombinasi keyword utama + sinonim ---
POST_SINONIM_EXCLUDE_RULES: dict[str, dict[str, list[str]]] = {
    "Pembangkit listrik nuklir ": {
        "nuklir ": [
            "senjata", "senjata nuklir", "rudal", "weapon",
            "bom nuklir", "hulu ledak", "warhead", "nuclear weapon",
            "nuclear bomb", "proliferasi", "uji coba nuklir",
            "korea utara", "iran nuklir",
        ],
    },
    "volume minyak ": {
        "minyak mentah ": ["harga"]
    }
}

# --- Post-exclude: exclude term bioenergi dari topik hulu migas ---
def _build_bioenergi_exclude_terms() -> list[str]:
    """Kumpulkan semua keyword utama + sinonim bioenergi sebagai exclude terms."""
    bioenergi_keys = ["biodiesel ", "bioetanol ", "SAF "]
    terms: set[str] = set()
    for key in bioenergi_keys:
        terms.add(key.strip())
        for sinonim in SINONIM_DICT.get(key, []):
            terms.add(sinonim.strip())
    return list(terms)

POST_EXCLUDE_RULES: dict[str, list[str]] = {
    "harga minyak ": _build_bioenergi_exclude_terms(),
    "volume minyak ": _build_bioenergi_exclude_terms(),
    "harga produk kilang pertamina ": _build_bioenergi_exclude_terms(),
    "volume produk kilang pertamina ": _build_bioenergi_exclude_terms(),
    "RON 92 ": _build_bioenergi_exclude_terms(),
    "RUPTL ": ["kesehatan"],
    "LCOE ": ["kesehatan"],
    "Pembangkit listrik nuklir ": ["kesehatan"],
    "harga minyak ": ["minyak goreng"]
}


# SUB-CATEGORY KEYWORD FILTERS (EBT / WTE / NUKLIR dari RUPTL)

EBT_KEYWORDS: list[str] = [
    "PLTA ", "PLTS ", "PLTB ", "BESS ", "PLTBm ", "panas bumi ", "PLTP ", "PLTBg ",
    # "listrik ", "pembangkit ", "transmisi ", "distribusi ", "elektrifikasi ",
    "PLN ", "IPP ", "PJBL ", "ketenagalistrikan ",
]
WTE_KEYWORDS:    list[str] = ["PLTSa "]
NUKLIR_KEYWORDS: list[str] = ["nuklir ", "PLTN "]


# SCRAPING SOURCES PER KEYWORD

SUMBER_DICT: dict[str, list] = {
    # ### Makroekonomi ###
    "indeks risiko geopolitik ": [main_bloomberg_technoz],
    "indeks volatilitas ": [main_bloomberg_technoz],
    "kurs ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "ihsg ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    # WIP (asyifashfr, 2026-07-13): CNBC-only + CNBC_RELEVANCE_RULES relevance filter,
    # kept as-is rather than reverted to the old multi-source list below.
    "inflasi ": [
        # scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo,
        main_cnbc,
        # main_bps
        ],
    "bi rate ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    "indonia ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    "indeks sales retail ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    "indeks kepercayaan konsumen ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bank_indonesia],
    "indeks kinerja manufaktur ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "indeks kinerja jasa ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc],
    "neraca perdagangan ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],
    "pertumbuhan domestik bruto ": [scrape_kontan, main_bisnis_indonesia, main_kompas, scrape_tempo, main_cnbc, main_bps],

    # ### Hulu Migas ###
    "harga minyak ": [scrape_kontan_bbm, main_bisnis_indonesia, main_bloomberg_technoz],
    "volume minyak ": [scrape_kontan_bbm, main_bisnis_indonesia, main_bloomberg_technoz],

    # ### Produk Kilang Pertamina ###
    "harga produk kilang pertamina ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    # "volume produk kilang pertamina ": left disabled (asyifashfr, main) — no reason on record, not re-enabling.
    # "volume produk kilang pertamina ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "RON 92 ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],

    # ## Petrokimia Hulu ###
    "Petrochemical ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],

    # ## Bioenergi
    "biodiesel ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "SAF ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "bioetanol ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],

    ### Ketenagalistrikan, EBT ###
    "RUPTL ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "LCOE ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "WTE ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
    "Pembangkit listrik nuklir ": [scrape_kontan_biodiesel, main_bisnis_indonesia, main_bloomberg_technoz],
}


# SHEET -> KEYWORD MAPPING & ACTIVE SHEETS

SHEET_TO_KEYWORD: dict[str, str] = {
    # ### Makroekonomi ###
    "(News)Indeks Risiko Geopolitik": "indeks risiko geopolitik ",
    "(News)Indeks Volatilitas": "indeks volatilitas ",
    "(News)Kurs": "kurs ",
    "(News)IHSG": "ihsg ",
    "(News)Inflasi": "inflasi ",
    "(News)BI Rate": "bi rate ",
    "(News)Indonia": "indonia ",
    "(News)Indeks Penjualan Ritel": "indeks sales retail ",
    "(News)Indeks Kepercayaan Knsmn": "indeks kepercayaan konsumen ",
    "(News)Indeks Kinerja Manufaktur": "indeks kinerja manufaktur ",
    "(News)Indeks Kinerja Jasa": "indeks kinerja jasa ",
    "(News)Neraca Perdagangan": "neraca perdagangan ",
    "(News)PDB": "pertumbuhan domestik bruto ",

    # ### Hulu Migas ###
    "(News)Harga Minyak": "harga minyak ",
    "(News)Volume Minyak": "volume minyak ",

    # ### Produk Kilang Pertamina ###
    "(News)Harga Produk Kilang": "harga produk kilang pertamina ",
    # "(News)Volume Produk Kilang": left disabled (asyifashfr, main), not re-enabling.
    # "(News)Volume Produk Kilang": "volume produk kilang pertamina ",
    "(News)Crackspread BBM": "RON 92 ",

    # ### Petrokimia Hulu ###
    "(News)Crackspread Non-BBM": "Petrochemical ",

    # ### Bioenenergi ###
    "(News)Biodiesel": "biodiesel ",
    "(News)SAF": "SAF ",
    "(News)Bioetanol": "bioetanol ",

    ### Ketenagalistrikan, EBT ###
    "(News)RUPTL": "RUPTL ",
    "(News)EBT": "LCOE ",
    "(News)WTE": "WTE ",
    "(News)Nuklir": "Pembangkit listrik nuklir ",
}

ACTIVE_SHEETS: list[str] = [
    # ### Makroekonomi ###
    "(News)Indeks Risiko Geopolitik",
    "(News)Indeks Volatilitas",
    "(News)Kurs",
    "(News)IHSG",
    "(News)Inflasi",
    "(News)BI Rate",
    "(News)Indonia",
    "(News)Indeks Penjualan Ritel",
    "(News)Indeks Kepercayaan Knsmn",
    "(News)Indeks Kinerja Manufaktur",
    "(News)Indeks Kinerja Jasa",
    "(News)Neraca Perdagangan",
    "(News)PDB",

    ### Hulu Migas ###
    "(News)Harga Minyak",
    "(News)Volume Minyak",

    # ### Produk Kilang Pertamina ###
    "(News)Harga Produk Kilang",
    # "(News)Volume Produk Kilang": left disabled (asyifashfr, main), not re-enabling.
    "(News)Crackspread BBM",

    # ### Petrokimia Hulu ###
    "(News)Crackspread Non-BBM",

    # ### Bioenergi ###
    "(News)Biodiesel",
    "(News)SAF",
    "(News)Bioetanol",

    ### Ketenagalistrikan, EBT ###
    "(News)RUPTL",
    "(News)EBT",
    "(News)WTE",
    "(News)Nuklir",
]


# COLUMN STANDARDIZATION

SOURCE_NAME_MAP: dict[str, str] = {
    "KONTAN_BBM":       "KONTAN",
    "KONTAN_BIODIESEL": "KONTAN",
    "GOOGLE_NEWS_CNN":  "CNN",
    "GOOGLE_NEWS_CNBC": "CNBC",
    "NEWS_SAP":         "S&P",
}

COLUMN_RENAME_MAP: dict[str, str] = {
    "Judul":   "title",
    "judul":   "title",
    "Title":   "title",
    "Tanggal": "date",
    "tanggal": "date",
    "Date":    "date",
    "Link":    "url",
    "link":    "url",
    "URL":     "url",
    "Konten":  "content",
    "konten":  "content",
    "Content": "content",
}

REQUIRED_COLUMNS: list[str] = ["title", "date", "url", "content"]
COLUMN_ORDER:     list[str] = ["title", "date", "url", "content", "source", "keyword", "matched_rule"]
EMPTY_DF = pd.DataFrame(columns=COLUMN_ORDER)


# HELPER FUNCTIONS

def _clean_date(date_str) -> str:
    """Normalize a date value to YYYY-MM-DD or 'N/A'."""
    if pd.isna(date_str) or date_str in ("N/A", "-"):
        return "N/A"
    date_str = str(date_str).strip().split("T")[0].split(" ")[0]
    return date_str if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str) else "N/A"

def standardize_format(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, fill missing required columns, and normalize dates."""
    if df is None or df.empty:
        return EMPTY_DF.copy()
    df = df.rename(columns=COLUMN_RENAME_MAP)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "N/A"
    df["date"] = df["date"].apply(_clean_date)
    existing_cols = [col for col in COLUMN_ORDER if col in df.columns]
    return df[existing_cols]

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate rows based on URL."""
    if df.empty:
        return df
    return df.drop_duplicates(subset=["url"], keep="first")

def remove_empty_content(df: pd.DataFrame) -> pd.DataFrame:
    """Buang artikel dengan konten kosong atau N/A (misal: epaper paywall)."""
    if df.empty:
        return df
    mask = (
        df["content"].notna() &
        (df["content"].str.strip() != "N/A") &
        (df["content"].str.strip() != "")
    )
    removed = len(df) - mask.sum()
    if removed > 0:
        print(f"    Empty content removed: {removed} article(s)")
    return df[mask].copy()

def generate_date_range(start_date: str, end_date: str) -> list[str]:
    """Generate list of dates between start_date and end_date (inclusive, YYYY-MM-DD)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end   = datetime.strptime(end_date,   "%Y-%m-%d")
    if start > end:
        raise ValueError(f"start_date ({start_date}) tidak boleh lebih besar dari end_date ({end_date})")
    dates, current = [], start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


# FILTER / EXCLUDE FUNCTIONS

def apply_global_exclude(df: pd.DataFrame) -> pd.DataFrame:
    """Buang artikel yang mengandung keyword hukum/korupsi."""
    if df.empty:
        return df
    pattern = "|".join(GLOBAL_EXCLUDE_KEYWORDS)
    mask = (
        df["title"].str.contains(pattern, case=False, na=False) |
        df["content"].str.contains(pattern, case=False, na=False)
    )
    removed = mask.sum()
    print(f"    Global exclude: {removed} article(s) removed")
    return df[~mask].copy()

def apply_post_exclude(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """Buang artikel yang mengandung keyword bioenergi dari topik hulu migas."""
    if df.empty:
        return df
    exclude_terms = POST_EXCLUDE_RULES.get(keyword)
    if not exclude_terms:
        return df
    pattern = "|".join(re.escape(t) for t in exclude_terms)
    mask = (
        df["title"].str.contains(pattern, case=False, na=False) |
        df["content"].str.contains(pattern, case=False, na=False)
    )
    removed = mask.sum()
    print(f"    Post-exclude '{keyword}': {removed} article(s) removed")
    return df[~mask].copy()

def apply_post_sinonim_exclude(df: pd.DataFrame, keyword: str, kata: str) -> pd.DataFrame:
    """
    Buang artikel yang mengandung exclude terms spesifik untuk
    kombinasi keyword utama + sinonim tertentu.
    Contoh: keyword 'Pembangkit listrik nuklir', sinonim 'nuklir' -> buang artikel senjata nuklir.
    """
    if df.empty:
        return df
    sinonim_rules = POST_SINONIM_EXCLUDE_RULES.get(keyword, {})
    exclude_terms = sinonim_rules.get(kata)
    if not exclude_terms:
        return df
    pattern = "|".join(re.escape(t) for t in exclude_terms)
    mask = (
        df["title"].str.contains(pattern, case=False, na=False) |
        df["content"].str.contains(pattern, case=False, na=False)
    )
    removed = mask.sum()
    print(f"    Sinonim exclude '{kata}': {removed} article(s) removed")
    return df[~mask].copy()

def _filter_by_keywords(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    """Return rows whose 'keyword' column matches any of the given keywords."""
    if df is None or df.empty:
        return EMPTY_DF.copy()
    pattern = "|".join(keywords)
    mask = df["keyword"].str.contains(pattern, case=False, na=False)
    return df[mask].copy()

def filter_ebt_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    """Filter RUPTL results to rows matching EBT-related keywords."""
    return _filter_by_keywords(df, EBT_KEYWORDS)

def filter_wte_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    """Filter RUPTL results to rows matching WTE-related keywords."""
    return _filter_by_keywords(df, WTE_KEYWORDS)

def filter_nuklir_from_ruptl(df: pd.DataFrame) -> pd.DataFrame:
    """Filter RUPTL results to rows matching nuclear-related keywords."""
    return _filter_by_keywords(df, NUKLIR_KEYWORDS)


# CORE SCRAPING LOGIC
def _find_matched_rule(row: pd.Series, terms: list[str]) -> str | None:
    """
    Cari term pertama yang cocok di judul atau konten artikel.
    Return format: 'title: {term}' atau 'content: {term}', atau None jika tidak ada.
    """
    for term in terms:
        if re.search(re.escape(term), str(row.get("title", "")), re.IGNORECASE):
            return f"title: {term}"
        if re.search(re.escape(term), str(row.get("content", "")), re.IGNORECASE):
            return f"content: {term}"
    return None

# Circuit breaker: skip a source after this many consecutive real failures
# (exceptions/timeouts -- NOT empty results, since many synonyms are niche
# and legitimately return nothing, and that shouldn't count against a source
# that's working fine). Rate-limited/down sources otherwise get retried on
# every remaining keyword across all sheets for no benefit.
#
# A disabled source isn't dead forever -- after CIRCUIT_BREAKER_COOLDOWN_SECONDS
# it gets one probe retry. Success clears the streak and re-enables it fully;
# another real failure just pushes the cooldown out again. Without this, a
# source down for 10 minutes (deploy, transient block) would stay skipped for
# the rest of a multi-hour run even after it recovered.
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 900
_source_fail_streak: dict[str, int] = {}
_source_disabled_at: dict[str, float] = {}

# Hard wall-clock deadline per source call. A source's own request timeout
# doesn't cover a stuck DNS lookup (see call_with_hard_timeout) -- generous
# enough for a legitimate multi-request scrape (sitemap crawl + several
# article content fetches, or a Selenium page load), far below the scale
# of a hang that can eat hours.
SCRAPE_FUNC_TIMEOUT_SECONDS = 120


def scrape_keyword(keyword: str, tanggal_filter: str) -> pd.DataFrame:
    """
    Scrape all synonyms of a keyword from all configured sources, apply
    post-filters where defined, and return a combined standardized DataFrame.
    """
    hasil_final = pd.DataFrame()
    semua_keyword  = [keyword] + SINONIM_DICT.get(keyword, [])
    sumber         = SUMBER_DICT.get(keyword, [main_kompas, main_bisnis_indonesia, scrape_tempo, scrape_kontan])
    post_filter_rules = POST_FILTER_RULES.get(keyword, {})

    for kata in semua_keyword:
        print(f"\n  Keyword: '{kata}'")
        hasil_list: list[pd.DataFrame] = []

        for scrape_func in sumber:
            raw_name    = scrape_func.__name__.replace("scrape_", "").replace("main_", "").upper()
            nama_sumber = SOURCE_NAME_MAP.get(raw_name, raw_name)

            disabled_at = _source_disabled_at.get(nama_sumber)
            if disabled_at is not None:
                cooldown_left = CIRCUIT_BREAKER_COOLDOWN_SECONDS - (time.time() - disabled_at)
                if cooldown_left > 0:
                    print(f"    Skip {nama_sumber} (circuit breaker: {CIRCUIT_BREAKER_THRESHOLD}x gagal beruntun, cooldown {int(cooldown_left / 60)}m lagi).")
                    continue
                print(f"    Cooldown {nama_sumber} selesai, coba lagi...")

            print(f"    Scraping from {nama_sumber}...")

            try:
                data = call_with_hard_timeout(
                    scrape_func, kata, tanggal_filter,
                    timeout=SCRAPE_FUNC_TIMEOUT_SECONDS,
                )
                if isinstance(data, pd.DataFrame):
                    df_temp = data
                elif data:
                    df_temp = pd.DataFrame(data)
                else:
                    df_temp = pd.DataFrame()

                if not df_temp.empty:
                    _source_fail_streak[nama_sumber] = 0
                    _source_disabled_at.pop(nama_sumber, None)
                    df_temp["source"] = nama_sumber
                    df_temp["matched_rule"] = "N/A"

                    df_temp = standardize_format(df_temp)
                    df_temp = remove_empty_content(df_temp)

                    if nama_sumber == "CNBC" and kata in CNBC_RELEVANCE_RULES:
                        before        = len(df_temp)
                        terms         = CNBC_RELEVANCE_RULES[kata]
                        matched_rules = df_temp.apply(lambda row: _find_matched_rule(row, terms), axis=1)
                        mask          = matched_rules.notna()
                        df_temp       = df_temp[mask].copy()
                        df_temp["matched_rule"] = matched_rules[mask].values
                        after = len(df_temp)
                        if before - after > 0:
                            print(f"    CNBC relevance filter '{kata}': {before} → {after} ({before - after} removed)")

                    hasil_list.append(df_temp)
                    print(f"    {len(df_temp)} article(s) from {nama_sumber}.")
                else:
                    # No match for this synonym -- not a source failure. Many
                    # synonyms are niche and legitimately return nothing; only
                    # exceptions/timeouts should burn down the circuit breaker,
                    # or a source with zero matches for the day gets wrongly
                    # killed for every remaining sheet in the run. A clean
                    # empty response also proves the source itself is up, so
                    # it clears a pending cooldown same as a real match would.
                    _source_fail_streak[nama_sumber] = 0
                    _source_disabled_at.pop(nama_sumber, None)
                    print(f"    No articles from {nama_sumber}.")

            except TimeoutError as exc:
                print(f"    Failed to scrape {nama_sumber}: {exc}")
                _source_fail_streak[nama_sumber] = _source_fail_streak.get(nama_sumber, 0) + 1
                # The abandoned thread may still be driving the shared Selenium
                # session -- drop it so the next call gets a fresh browser
                # instead of contending with a possibly still-running one.
                if nama_sumber == "CNBC":
                    close_cnbc_driver()
                elif nama_sumber == "BANK_INDONESIA":
                    close_bank_indonesia_driver()

            except Exception as exc:
                print(f"    Failed to scrape {nama_sumber}: {exc}")
                _source_fail_streak[nama_sumber] = _source_fail_streak.get(nama_sumber, 0) + 1

            if _source_fail_streak.get(nama_sumber, 0) >= CIRCUIT_BREAKER_THRESHOLD:
                _source_disabled_at[nama_sumber] = time.time()
                print(f"    {nama_sumber} dinonaktifkan {CIRCUIT_BREAKER_COOLDOWN_SECONDS // 60}m ({CIRCUIT_BREAKER_THRESHOLD}x gagal beruntun).")

        if hasil_list:
            df_kata = pd.concat(hasil_list, ignore_index=True)
            df_kata["keyword"] = kata

            # Post-filter: artikel harus mengandung secondary term (include filter)
            secondary_terms = post_filter_rules.get(kata)
            if secondary_terms:
                before  = len(df_kata)
                pattern = "|".join(secondary_terms)
                mask = (
                    df_kata["title"].str.contains(pattern, case=False, na=False) |
                    df_kata["content"].str.contains(pattern, case=False, na=False)
                )
                df_kata = df_kata[mask].copy()
                after   = len(df_kata)
                print(f"    Post-filter '{kata}': {before} -> {after} article(s) ({before - after} removed)")

            df_kata = apply_global_exclude(df_kata)
            df_kata = apply_post_exclude(df_kata, keyword)
            df_kata = apply_post_sinonim_exclude(df_kata, keyword, kata)
            hasil_final = pd.concat([hasil_final, df_kata], ignore_index=True)

    return hasil_final if not hasil_final.empty else EMPTY_DF.copy()


# MAIN

def main() -> None:
    try:
        _main_impl()
    finally:
        # Shared Selenium drivers (CNBC, Bank Indonesia) are reused across
        # keywords for the whole run -- close them here so no Chrome process
        # lingers after the script exits, success or failure either way.
        close_cnbc_driver()
        close_bank_indonesia_driver()


def _main_impl() -> None:
    print("\n" + "=" * 60)
    print("NEWS SCRAPING")
    print("=" * 60)

    # === KONFIGURASI TANGGAL ===
    # Pilih salah satu mode:

    # Mode 1: Satu tanggal spesifik
    # tanggal_list = ["2026-04-21"]

    if os.getenv("CI"):
        tanggal_list = [(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]
    else:
        # Mode 2: Range tanggal
        START_DATE   = "2026-04-24"
        END_DATE     = "2026-04-24"
        tanggal_list = generate_date_range(START_DATE, END_DATE)

    # Mode 3: Kemarin
    # tanggal_list = [(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")]

    # Mode 4: Tanpa filter tanggal (semua artikel)
    # tanggal_list = [None]
    # ===========================

    print(f"\nAkan scraping untuk {len(tanggal_list)} tanggal:")
    for t in tanggal_list:
        print(f"  - {t}")

    # --- Load existing sheets SEKALI di awal ---
    print(f"\nLoading existing data...")
    all_sheets = storage.read_all_news_sheets(ACTIVE_SHEETS)

    # --- Loop per tanggal ---
    total_dates = len(tanggal_list)

    for date_idx, tanggal_filter in enumerate(tanggal_list, 1):
        print("\n" + "=" * 60)
        print(f"SCRAPING TANGGAL {date_idx}/{total_dates}: {tanggal_filter}")
        print("=" * 60)

        for sheet_name in ACTIVE_SHEETS:
            keyword_asli = SHEET_TO_KEYWORD.get(sheet_name)
            if not keyword_asli:
                print(f"\n[Main] No keyword mapping for '{sheet_name}' — skipping.")
                continue

            print(f"\n{'-' * 60}")
            print(f"Sheet  : {sheet_name}")
            print(f"Keyword: {keyword_asli}")
            print(f"Tanggal: {tanggal_filter}")
            print(f"{'-' * 60}")

            hasil_df = scrape_keyword(keyword_asli, tanggal_filter)

            # Merge dengan data existing di memori
            existing = all_sheets.get(sheet_name, pd.DataFrame())
            if not existing.empty:
                combined_df = pd.concat([existing, hasil_df], ignore_index=True)
                print(f"\n  Data existing : {len(existing)} row(s)")
                print(f"  Data baru     : {len(hasil_df)} row(s)")
            else:
                combined_df = hasil_df
                print(f"\n  Data baru: {len(hasil_df)} row(s)")

            combined_df = remove_duplicates(combined_df)
            all_sheets[sheet_name] = combined_df
            print(f"  Total (after dedup): {len(combined_df)} row(s)")

            print("\nIstirahat 30 detik antar keyword...")
            time.sleep(30)

        # Simpan ke OneDrive setiap selesai 1 tanggal
        print(f"\n{'=' * 60}")
        print(f"MENYIMPAN PROGRES — Selesai tanggal {tanggal_filter} ({date_idx}/{total_dates})")
        print(f"{'=' * 60}")

        try:
            storage.write_news_file(all_sheets)
            print(f"Berhasil disimpan.")
        except Exception as exc:
            print(f"Error saat menyimpan setelah tanggal {tanggal_filter}: {exc}")
            print("Melanjutkan ke tanggal berikutnya...")

        # Jeda antar tanggal (kecuali tanggal terakhir)
        if date_idx < total_dates:
            jeda = 60
            print(f"\nIstirahat {jeda} detik sebelum tanggal berikutnya...")
            time.sleep(jeda)

    # --- Summary akhir ---
    print("\n" + "=" * 60)
    print("SELESAI SEMUA TANGGAL!")
    print(f"Sheets          : {len(ACTIVE_SHEETS)}")
    print(f"Tanggal diproses: {tanggal_list[0]} s/d {tanggal_list[-1]}")
    print(f"Total baris     : {sum(len(df) for df in all_sheets.values())}")
    print("=" * 60 + "\n")


# ENTRY POINT

if __name__ == "__main__":
    main()
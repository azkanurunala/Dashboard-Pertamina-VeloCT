
import asyncio
import pandas as pd
import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from glob import glob
import re

# Add azure_functions to path
sys.path.append(os.path.join(os.getcwd(), 'azure_functions'))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.getcwd(), 'azure_functions', '.env')
    if not os.path.exists(env_path):
        # Fallback if running from inside azure_functions/scripts
        env_path = os.path.join(os.getcwd(), '..', '.env')
    if not os.path.exists(env_path):
        # Fallback if running from inside azure_functions/scripts (another level)
        env_path = os.path.join(os.getcwd(), '..', '..', '.env')
    load_dotenv(env_path)
except ImportError:
    pass

# Ensure the DB handler can find the connection string
if os.getenv('SQL_SERVER_CONNECTION_STRING') is None and os.getenv('DatabaseConnectionString'):
    os.environ['SQL_SERVER_CONNECTION_STRING'] = os.getenv('DatabaseConnectionString')

from shared.database_handler import DatabaseHandler
from shared.config import config_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataSeeder:
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler
        self.month_map = {
            'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
            'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12,
            'January': 1, 'February': 2, 'March': 3, 'May': 5, 'June': 6, 'July': 7, 'August': 8, 'October': 10, 'December': 12
        }

    def parse_date(self, date_val: Any) -> Optional[datetime]:
        """Robust date parsing for various formats."""
        if pd.isna(date_val):
            return None
        if isinstance(date_val, (datetime, pd.Timestamp)):
            return date_val.to_pydatetime() if hasattr(date_val, 'to_pydatetime') else date_val
        
        date_str = str(date_val).strip()
        # Handle ISO with T
        if 'T' in date_str:
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                pass

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%b-%y", "%Y%m%d", "%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Handle Month/Year format (e.g., 1/2000)
        match = re.match(r'^(\d{1,2})/(\d{4})$', date_str)
        if match:
            return datetime(int(match.group(2)), int(match.group(1)), 1)

        logger.warning(f"Could not parse date: {date_val}")
        return None

    def clean_float(self, val: Any) -> float:
        """Convert string numbers with commas/symbols to float."""
        if pd.isna(val) or val == '':
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        
        cleaned = str(val).replace(',', '').replace('$', '').replace('IDR', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    async def bulk_insert(self, table_name: str, data: List[Dict[str, Any]]):
        """Helper to bulk insert data in chunks."""
        if not data:
            return 0
        
        chunk_size = 500
        total_saved = 0
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            saved = await self.db_handler.save_structured_data(table_name, chunk)
            total_saved += saved
        return total_saved

    async def seed_file(self, file_path: str, table_name: str, mapping_func):
        """Generic method to read, transform, and seed a file."""
        filename = os.path.basename(file_path)
        logger.info(f"🚀 Seeding {filename} to {table_name}...")
        
        try:
            if filename.endswith('.csv'):
                # Try common encodings and delimiters
                df = None
                encodings = ['utf-8-sig', 'latin-1', 'cp1252', 'utf-16']
                delimiters = [',', ';', '\t']
                
                for encoding in encodings:
                    for delimiter in delimiters:
                        try:
                            temp_df = pd.read_csv(file_path, encoding=encoding, sep=delimiter)
                            if len(temp_df.columns) > 1:
                                df = temp_df
                                logger.info(f"  Read {filename} with {encoding} and delimiter '{delimiter}'")
                                break
                        except Exception:
                            continue
                    if df is not None: break
                
                if df is None: 
                    # Fallback to default
                    try:
                        df = pd.read_csv(file_path, encoding='utf-8-sig')
                    except:
                        raise Exception("Could not read CSV with any encoding/delimiter")
            else:
                # Handle Excel - try to read specific sheets if mapped
                sheet_name = None
                if 'Input_Manual' in filename:
                    if table_name == 'data_fossil': sheet_name = '(Data)Input_Fosil'
                    elif table_name == 'data_fossil_prediction': sheet_name = '(Data)Input_Fosil_Prediction'
                
                df = pd.read_excel(file_path, sheet_name=sheet_name) if sheet_name else pd.read_excel(file_path)

            transformed_data = mapping_func(df)
            
            if transformed_data:
                logger.info(f"  Saving {len(transformed_data)} rows...")
                # Chunking for efficiency
                chunk_size = 500
                total_saved = 0
                for i in range(0, len(transformed_data), chunk_size):
                    chunk = transformed_data[i:i + chunk_size]
                    saved = await self.db_handler.save_structured_data(table_name, chunk)
                    total_saved += saved
                logger.info(f"  ✅ Successfully seeded {filename} ({total_saved} rows)")
            else:
                logger.warning(f"  ⚠️ No data transformed for {filename}")

        except Exception as e:
            logger.error(f"  ❌ Failed to seed {filename}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # --- Mapping Functions ---

    def map_biodiesel(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        for _, row in df.iterrows():
            data.append({
                'published_date': self.parse_date(row.get('Date')),
                'hip_month': str(row.get('Bulan HIP', '')),
                'price_idr_liter': self.clean_float(row.get('HIP Biodiesel IDR/L'))
            })
        return data

    def map_bioetanol(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Date,Bulan HIP,HIP Bioetanol IDR/L,Harga Tetes Tebu
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'date': self.parse_date(row.get('Date')),
                    'bulan_hip': str(row.get('Bulan HIP', '')),
                    'hip_bioetanol_idr_l': self.clean_float(row.get('HIP Bioetanol IDR/L')),
                    'harga_tetes_tebu': self.clean_float(row.get('Harga Tetes Tebu'))
                })
            except Exception as e:
                logger.warning(f"Error mapping Bioetanol row: {e}")
                continue
        return data

    def map_harga_ebt(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # No,Lokasi,Provinsi,Jenis EBT,Faktor Lokasi,Kelompok HPT,Stage,cent $/kWh,LCOE cent$/kWh,Battery
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'no': int(self.clean_float(row.get('No'))),
                    'lokasi': str(row.get('Lokasi', '')),
                    'provinsi': str(row.get('Provinsi', '')),
                    'jenis_ebt': str(row.get('Jenis EBT', '')),
                    'faktor_lokasi': self.clean_float(row.get('Faktor Lokasi')),
                    'kelompok_hpt': str(row.get('Kelompok HPT', '')),
                    'stage': int(self.clean_float(row.get('Stage'))),
                    'cent_usd_kwh': self.clean_float(row.get('cent $/kWh')),
                    'lcoe_cent_usd_kwh': self.clean_float(row.get('LCOE cent$/kWh')),
                    'battery': self.clean_float(row.get('Battery'))
                })
            except Exception as e:
                # logger.warning(f"Error mapping Harga EBT row: {e}")
                continue
        return data

    def map_cpo(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        for _, row in df.iterrows():
            data.append({
                'upload_date': self.parse_date(row.get('Upload_Dates')),
                'price_date': self.parse_date(row.get('Dates')),
                'px_last': self.clean_float(row.get('PX_LAST'))
            })
        return data

    def map_crackspread_bbm(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        for _, row in df.iterrows():
            try:
                year = int(row.get('year', 0))
                month = int(row.get('month', 0))
                if year > 0 and month > 0:
                    assess_date = datetime(year, month, 1)
                    
                    data.append({
                        'assess_date': assess_date,
                        'val_ron92': self.clean_float(row.get('price_RON92')),
                        'val_ron95': self.clean_float(row.get('price_RON95')),
                        'val_ron97': self.clean_float(row.get('price_RON97')),
                        'val_fo05': self.clean_float(row.get('price_FO05')),
                        'val_jetkero': self.clean_float(row.get('price_JetKero')),
                        'val_go50': self.clean_float(row.get('price_GO50')),
                        'val_go2500': self.clean_float(row.get('price_GO2500')),
                        'val_brent': self.clean_float(row.get('price_Brent')),
                        'cs_ron92': self.clean_float(row.get('price_RON92_crackspread')),
                        'cs_ron95': self.clean_float(row.get('price_RON95_crackspread')),
                        'cs_ron97': self.clean_float(row.get('price_RON97_crackspread')),
                         # Note: CSV headers might differ from expected logic, adjusting based on audit
                         # Audit: price_RON92, price_RON95...
                    })
            except Exception as e:
                # logger.warning(f"Skipping row in crackspread: {e}")
                pass
        return data

    def map_petroch_prices(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        for _, row in df.iterrows():
            data.append({
                'year': int(row.get('Year', 0)),
                'month': int(row.get('Month', 0)),
                # Audit shows keys like 'Price_Paraxylene'
                'price_paraxylene': self.clean_float(row.get('Price_Paraxylene')),
                'price_propylene': self.clean_float(row.get('Price_Propylene')),
                'price_benzene': self.clean_float(row.get('Price_Benzene')),
                'price_butane': self.clean_float(row.get('Price_Butane')),
                'price_propane': self.clean_float(row.get('Price_Propane')),
                'price_lpg': self.clean_float(row.get('Price_LPG')),
                'price_brent': self.clean_float(row.get('Price_Brent')),
                'cs_paraxylene': self.clean_float(row.get('Price_Paraxylene_crackspread')),
                'cs_propylene': self.clean_float(row.get('Price_Propylene_crackspread')),
                'cs_benzene': self.clean_float(row.get('Price_Benzene_crackspread')),
                'cs_lpg': self.clean_float(row.get('Price_LPG_crackspread'))
            })
        return data

    def map_fossil_prediction(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        # Support both CSV colon-separated and Excel structured
        for _, row in df.iterrows():
            # If CSV had semicolon, it might be parsed now.
            try:
                data.append({
                    'prediction_year': int(row.get('Tahun', 0)),
                    'brent': self.clean_float(row.get('Brent')),
                    'gasoline': self.clean_float(row.get('Gasoline')),
                    'diesel': self.clean_float(row.get('Diesel')),
                    'avtur': self.clean_float(row.get('Avtur')),
                    'fo05_price': self.clean_float(row.get('FO05 (Price)')),
                    'go2500_price': self.clean_float(row.get('GO2500 (Price)')),
                    'go50_price': self.clean_float(row.get('GO50 (Price)')),
                    'jetkero_price': self.clean_float(row.get('JetKero (Price)')),
                    'ron92_price': self.clean_float(row.get('RON92 (Price)')),
                    'ron95_price': self.clean_float(row.get('RON95 (Price)')),
                    'ron97_price': self.clean_float(row.get('RON97 (Price)')),
                    'fo05_cs': self.clean_float(row.get('FO05 (Crack Spread)')),
                    'go2500_cs': self.clean_float(row.get('GO2500 (Crack Spread)')),
                    'go50_cs': self.clean_float(row.get('GO50 (Crack Spread)')),
                    'jetkero_cs': self.clean_float(row.get('JetKero (Crack Spread)')),
                    'ron92_cs': self.clean_float(row.get('RON92 (Crack Spread)')),
                    'ron95_cs': self.clean_float(row.get('RON95 (Crack Spread)')),
                    'ron97_cs': self.clean_float(row.get('RON97 (Crack Spread)'))
                })
            except Exception:
                continue
        return data

    def map_iaea_nuclear_capacity(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)IAEA_Nuclear_Capacity.csv
        # Columns: Year,Total Net Electrical Capacity[GW],Number of Operated Reactors,Year-end Total Net Electrical Capacity[GW],Year-end Operational Reactors
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('Year'))),
                    'total_net_electrical_capacity_gw': self.clean_float(row.get('Total Net Electrical Capacity[GW]')),
                    'num_operated_reactors': int(self.clean_float(row.get('Number of Operated Reactors'))),
                    'year_end_total_net_electrical_capacity_gw': self.clean_float(row.get('Year-end Total Net Electrical Capacity[GW]')),
                    'year_end_operational_reactors': int(self.clean_float(row.get('Year-end Operational Reactors')))
                })
            except Exception as e:
                logger.warning(f"Error mapping IAEA Nuclear Capacity row: {e}")
                continue
        return data

    def map_iaea_electrical(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)IAEA_Electrical.csv
        # Columns: Year,"Net Electrical Capacity, GW(e)",Number of Operated Reactors with Data,Electricity Supplied[TW.h]
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('Year'))),
                    'net_electrical_capacity_gwe': self.clean_float(row.get('Net Electrical Capacity, GW(e)')),
                    'num_operated_reactors_with_data': int(self.clean_float(row.get('Number of Operated Reactors with Data'))),
                    'electricity_supplied_twh': self.clean_float(row.get('Electricity Supplied[TW.h]'))
                })
            except Exception as e:
                logger.warning(f"Error mapping IAEA Electrical row: {e}")
                continue
        return data

    def map_oil_prices(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source is (Data)Harga Minyak.csv
        # Columns: Tahun,Bulan,Harga,Tanggal,Harga_Brent
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('Tahun'))),
                    'month': str(row.get('Bulan', '')),
                    'price': self.clean_float(row.get('Harga')),
                    'date_raw': str(row.get('Tanggal', '')),
                    'brent_price': self.clean_float(row.get('Harga_Brent'))
                })
            except Exception as e:
                logger.warning(f"Error mapping Oil Prices row: {e}")
                continue
        return data

    def map_kurs(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        for _, row in df.iterrows():
            if len(row) < 3: continue
            dt = self.parse_date(row.iloc[0])
            val = self.clean_float(row.iloc[2])
            if dt and val > 0:
                data.append({
                    'indicator_date': dt,
                    'category': 'Kurs',
                    'indicator_name': 'USD/IDR',
                    'value': val
                })
        return data

    def map_fossil(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Mapped to (Data)Input_Manual.xlsx -> (Data)Input_Fosil in new plan
        # If using CSV, we rely on delimiter detection.
        data = []
        for _, row in df.iterrows():
             # Map keys with potential checks
            data.append({
                'time': self.parse_date(row.get('Time') or row.get('time')),
                'brent': self.clean_float(row.get('Brent')),
                'gasoline': self.clean_float(row.get('Gasoline')),
                'diesel': self.clean_float(row.get('Diesel')),
                'avtur': self.clean_float(row.get('Avtur'))
            })
        return data

    def map_wte_sumber(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)WTE_Sumber.csv
        # Columns: tahun, Nama Provinsi, Nama Kota/Kabupaten, ss_rumah_tangga, ss_perkantoran, ss_pasar, ss_perniagaan, ss_fasilitas_publik, ss_kawasan, ss_lain_lain
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('tahun'))),
                    'province': str(row.get('Nama Provinsi', '')),
                    'city_regency': str(row.get('Nama Kota/Kabupaten', '')),
                    'ss_rumah_tangga': self.clean_float(row.get('ss_rumah_tangga')),
                    'ss_perkantoran': self.clean_float(row.get('ss_perkantoran')),
                    'ss_pasar': self.clean_float(row.get('ss_pasar')),
                    'ss_perniagaan': self.clean_float(row.get('ss_perniagaan')),
                    'ss_fasilitas_publik': self.clean_float(row.get('ss_fasilitas_publik')),
                    'ss_kawasan': self.clean_float(row.get('ss_kawasan')),
                    'ss_lain_lain': self.clean_float(row.get('ss_lain_lain'))
                })
            except Exception as e:
                logger.warning(f"Error mapping WTE Sumber row: {e}")
                continue
        return data

    def map_wte_komposisi(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)WTE_Komposisi.csv
        # Columns: tahun, Nama Provinsi, Nama Kota/Kabupaten, sisa_makanan, kayu_ranting, kertas_karton, plastik, logam, kain, karet_kulit, kaca, lain_lain
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('tahun'))),
                    'province': str(row.get('Nama Provinsi', '')),
                    'city_regency': str(row.get('Nama Kota/Kabupaten', '')),
                    'sisa_makanan': self.clean_float(row.get('sisa_makanan')),
                    'kayu_ranting': self.clean_float(row.get('kayu_ranting')),
                    'kertas_karton': self.clean_float(row.get('kertas_karton')),
                    'plastik': self.clean_float(row.get('plastik')),
                    'logam': self.clean_float(row.get('logam')),
                    'kain': self.clean_float(row.get('kain')),
                    'karet_kulit': self.clean_float(row.get('karet_kulit')),
                    'kaca': self.clean_float(row.get('kaca')),
                    'lain_lain': self.clean_float(row.get('lain_lain'))
                })
            except Exception as e:
                logger.warning(f"Error mapping WTE Komposisi row: {e}")
                continue
        return data

    def map_wte_timbulan(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)WTE_Timbulan.csv
        # Columns: tahun, Nama Provinsi, Nama Kota/Kabupaten, timbulan_harian, timbulan_tahunan
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'year': int(self.clean_float(row.get('tahun'))),
                    'province': str(row.get('Nama Provinsi', '')),
                    'city_regency': str(row.get('Nama Kota/Kabupaten', '')),
                    'timbulan_harian': self.clean_float(row.get('timbulan_harian')),
                    'timbulan_tahunan': self.clean_float(row.get('timbulan_tahunan'))
                })
            except Exception as e:
                logger.warning(f"Error mapping WTE Timbulan row: {e}")
                continue
        return data

    def map_saf_uco(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # assessDate,value_UCO,value_SAF,modDate_UCO,modDate_SAF
        data = []
        for _, row in df.iterrows():
            data.append({
                'assess_date': self.parse_date(row.get('assessDate')),
                'value_uco': self.clean_float(row.get('value_UCO')),
                'value_saf': self.clean_float(row.get('value_SAF')),
                'mod_date_uco': self.parse_date(row.get('modDate_UCO')),
                'mod_date_saf': self.parse_date(row.get('modDate_SAF'))
            })
        return data

    def map_volatility(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Date,Last Price
        data = []
        for _, row in df.iterrows():
            data.append({
                'indicator_date': self.parse_date(row.get('Date')),
                'index_name': 'VIX',
                'index_value': self.clean_float(row.get('Last Price'))
            })
        return data

    def map_geopolitik(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        data = []
        # Data starts after messy headers. We use generic ilocs if column names are missing.
        for _, row in df.iterrows():
            if len(row) < 2: continue
            dt = self.parse_date(row.iloc[0])
            val = self.clean_float(row.iloc[1])
            if dt and val > 0:
                data.append({
                    'index_date': dt,
                    'region': 'World',
                    'gpr_value': val
                })
        return data

    def map_eia_market(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Bulan,Tahun,World Total Production,OPEC,Non-OPEC,Crude Oil,Other Liquids,World Total Consumption,OECD,Non-OECD,Next Release Date
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'bulan': str(row.get('Bulan', '')),
                    'tahun': int(row.get('Tahun', 0)),
                    'world_total_production': self.clean_float(row.get('World Total Production')),
                    'opec': self.clean_float(row.get('OPEC')),
                    'non_opec': self.clean_float(row.get('Non-OPEC')),
                    'crude_oil': self.clean_float(row.get('Crude Oil')),
                    'other_liquids': self.clean_float(row.get('Other Liquids')),
                    'world_total_consumption': self.clean_float(row.get('World Total Consumption')),
                    'oecd': self.clean_float(row.get('OECD')),
                    'non_oecd': self.clean_float(row.get('Non-OECD')),
                    'next_release_date': self.parse_date(row.get('Next Release Date'))
                })
            except Exception as e:
                logger.warning(f"Error mapping EIA row: {e}")
                continue
        return data

    def map_ebt_capacity(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Source: (Data)Kapasitas_EBT.csv
        # Columns: tahun,bulan,plta,pltm,pltmh,pltp,plts,plts_atap,pltb,pltbm,pltbg,pltsa,pltbn,plt_hybrid,total
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'tahun': int(self.clean_float(row.get('tahun'))),
                    'bulan': int(self.clean_float(row.get('bulan'))),
                    'plta': self.clean_float(row.get('plta')),
                    'pltm': self.clean_float(row.get('pltm')),
                    'pltmh': self.clean_float(row.get('pltmh')),
                    'pltp': self.clean_float(row.get('pltp')),
                    'plts': self.clean_float(row.get('plts')),
                    'plts_atap': self.clean_float(row.get('plts_atap')),
                    'pltb': self.clean_float(row.get('pltb')),
                    'pltbm': self.clean_float(row.get('pltbm')),
                    'pltbg': self.clean_float(row.get('pltbg')),
                    'pltsa': self.clean_float(row.get('pltsa')),
                    'pltbn': self.clean_float(row.get('pltbn')),
                    'plt_hybrid': self.clean_float(row.get('plt_hybrid')),
                    'total': self.clean_float(row.get('total'))
                })
            except Exception as e:
                logger.warning(f"Error mapping EBT Capacity row: {e}")
                continue
        return data

    def map_ruptl(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # Columns: No (number), Provinsi, Nama Sistem Tenaga Listrik, Jenis Pembangkit, 
        # Lokasi / Nama Pembangkit, Kapasitas (MW), Target COD Skenario RE Base, 
        # Target COD Skenario ARED, Status, Pengembang, Keterangan
        data = []
        for _, row in df.iterrows():
            try:
                data.append({
                    'number': int(self.clean_float(row.get('No'))),
                    'province': str(row.get('Provinsi', '')),
                    'electric_system': str(row.get('Nama Sistem Tenaga Listrik', '')),
                    'power_plant_type': str(row.get('Jenis Pembangkit', '')),
                    'project_name': str(row.get('Lokasi / Nama Pembangkit', '')),
                    'capacity_mw': self.clean_float(row.get('Kapasitas (MW)')),
                    'target_cod_re_base': str(row.get('Target COD Skenario RE Base', '')),
                    'target_cod_ared': str(row.get('Target COD Skenario ARED', '')),
                    'status': str(row.get('Status', '')),
                    'developer': str(row.get('Pengembang', '')),
                    'notes': str(row.get('Keterangan ', ''))  # Note the space in column name
                })
            except Exception as e:
                logger.warning(f"Error mapping RUPTL row: {e}")
                continue
        return data

async def main():
    config_manager.reload()
    try:
        db_config = await config_manager.get_database_config()
        db_handler = DatabaseHandler(db_config)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    seeder = DataSeeder(db_handler)
    data_dir = r'azure_functions\references\data'

    # Updated Mappings
    mappings = [
        ('(Data)Biodesel.csv', 'data_biodiesel_hip', seeder.map_biodiesel),
        ('(Data)Bioetanol.csv', 'data_bioetanol_hip', seeder.map_bioetanol),
        ('(Data)HargaEBT.csv', 'data_ebt_prices', seeder.map_harga_ebt),
        ('(Data)CPO.csv', 'data_cpo_prices', seeder.map_cpo),
        ('(Data)Crackspread_BBM.csv', 'data_oil_crackspreads', seeder.map_crackspread_bbm),
        ('(Data)Crackspread_NON_BBM.csv', 'data_petrochemical_prices', seeder.map_petroch_prices),
        ('(Data)Input_Fosil_Prediction.csv', 'data_fossil_prediction', seeder.map_fossil_prediction),
        ('(Data)IAEA_Electrical.csv', 'data_iaea_electrical', seeder.map_iaea_electrical),
        ('(Data)IAEA_Nuclear_Capacity.csv', 'data_iaea_nuclear_capacity', seeder.map_iaea_nuclear_capacity),
        ('(Data)Harga Minyak.csv', 'data_oil_prices', seeder.map_oil_prices),
        ('(Data)Kurs.csv', 'data_market_indicators', seeder.map_kurs),
        ('(Data)Input_Fosil.csv', 'data_fossil', seeder.map_fossil),
        ('(Data)SAF.csv', 'data_saf_uco_prices', seeder.map_saf_uco),
        ('(Data)Volatilitas.csv', 'data_volatility_index', seeder.map_volatility),
        ('(Data)Geopolitik.csv', 'data_geopolitical_risk_index', seeder.map_geopolitik),
        ('(Data)eia.csv', 'data_eia_market', seeder.map_eia_market),
        ('(Data)Kapasitas_EBT.csv', 'data_ebt_capacity', seeder.map_ebt_capacity),
        ('(Data)WTE_Timbulan.csv', 'data_wte_timbulan', seeder.map_wte_timbulan),
        ('(Data)WTE_Sumber.csv', 'data_wte_sumber', seeder.map_wte_sumber),
        ('(Data)WTE_Komposisi.csv', 'data_wte_komposisi', seeder.map_wte_komposisi),
        ('(Data)RUPTL.csv', 'data_ruptl_projects', seeder.map_ruptl),
    ]

    for pattern, table, func in mappings:
        file_path = os.path.join(data_dir, pattern)
        logger.info(f"Checking for file: {file_path}")
        if os.path.exists(file_path):
            await seeder.seed_file(file_path, table, func)
        else:
            logger.warning(f"NOT FOUND: {file_path}")

    with open(r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\status.txt', 'w') as f:
        f.write("COMPLETED AT " + datetime.now().isoformat())
    logger.info("🎯 All seeding tasks completed.")

if __name__ == "__main__":
    asyncio.run(main())

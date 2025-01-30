from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import WebDriverException, TimeoutException
import time
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import random
import psutil
import gc

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'
CONNECTION_TIME = 60
MAX_RETRIES = 3
RETRY_DELAY = 2

def get_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_percent = process.memory_percent()
    system_memory = psutil.virtual_memory()
    
    return {
        'process_rss': memory_info.rss / 1024 / 1024,  # MB
        'process_vms': memory_info.vms / 1024 / 1024,  # MB
        'process_percent': memory_percent,
        'system_total': system_memory.total / 1024 / 1024 / 1024,  # GB
        'system_used_percent': system_memory.percent
    }

def log_memory_status(user_id, stage):
    mem = get_memory_usage()
    logger.info(
        f"MEMORY [Usuário {user_id}] [{stage}] - "
        f"Processo: {mem['process_rss']:.1f}MB (RSS) / "
        f"{mem['process_vms']:.1f}MB (VMS) / "
        f"{mem['process_percent']:.1f}% | "
        f"Sistema: {mem['system_total']:.1f}GB total / "
        f"{mem['system_used_percent']:.1f}% usado"
    )

def check_system_resources():
    memory = psutil.virtual_memory()
    memory_status = memory.percent > 80
    log_memory_status('SYSTEM', 'Resource Check')
    return not memory_status

def create_driver(user_id):
    log_memory_status(user_id, 'Pre-Driver')
    
    if not check_system_resources():
        logger.warning(f"Usuário {user_id}: Recursos do sistema muito altos, aguardando...")
        time.sleep(5)
        
    for attempt in range(MAX_RETRIES):
        try:
            options = FirefoxOptions()
            
            # Configurações básicas do headless
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            # Otimizações de memória
            options.add_argument('--js-flags="--max-old-space-size=256"')
            options.add_argument('--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            
            if os.path.exists('/usr/bin/firefox-esr'):
                options.binary_location = '/usr/bin/firefox-esr'
            
            # Preferências otimizadas
            options.set_preference('javascript.enabled', True)
            options.set_preference('dom.webdriver.enabled', False)
            options.set_preference('browser.cache.disk.enable', False)
            options.set_preference('browser.cache.memory.enable', False)
            options.set_preference('browser.cache.offline.enable', False)
            options.set_preference('network.http.use-cache', False)
            options.set_preference('browser.sessionstore.enabled', False)
            options.set_preference('browser.startup.page', 0)
            options.set_preference('browser.download.manager.retention', 0)
            options.set_preference('privacy.trackingprotection.enabled', False)
            
            options.add_argument('--window-size=800,600')
            
            service = Service(
                executable_path=GECKODRIVER_PATH,
                log_path='/dev/null'
            )
            
            driver = webdriver.Firefox(service=service, options=options)
            
            log_memory_status(user_id, 'Post-Driver')
            gc.collect()
            
            return driver
            
        except Exception as e:
            error_msg = str(e).strip()
            if error_msg:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - {error_msg}")
            else:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - Timeout ou conexão perdida")
            
            time.sleep(RETRY_DELAY * (attempt + 1))
            gc.collect()
    
    return None

def simulate_user_access(user_id):
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
        log_memory_status(user_id, 'Start')
        
        driver = create_driver(user_id)
        
        if not driver:
            logger.error(f"Usuário {user_id}: Falha ao criar driver após {MAX_RETRIES} tentativas")
            return
        
        driver.set_page_load_timeout(30)
        url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
        
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)
                logger.info(f"Usuário {user_id}: Página carregada com sucesso")
                log_memory_status(user_id, 'Page Loaded')
                break
            except Exception as e:
                error_msg = str(e).strip()
                if error_msg:
                    logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} falhou - {error_msg}")
                else:
                    logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} falhou - Timeout")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(RETRY_DELAY)
        
        start_time = time.time()
        interaction_count = 0
        
        while time.time() - start_time < CONNECTION_TIME:
            log_memory_status(user_id, f'Interaction {interaction_count}')
            
            if not check_system_resources():
                logger.warning(f"Usuário {user_id}: Alto uso de memória detectado")
                break
                
            try:
                try:
                    dialog_backdrop = driver.find_element(By.CSS_SELECTOR, "div.q-dialog__backdrop")
                    if dialog_backdrop.is_displayed():
                        dialog_backdrop.click()
                        time.sleep(1)
                except:
                    pass
                
                wait = WebDriverWait(driver, 10)
                buttons = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
                )
                
                success = False
                for i in range(min(2, len(buttons))):
                    if click_button_safely(driver, buttons[i], user_id, i+1):
                        success = True
                        time.sleep(1)
                
                if success:
                    interaction_count += 1
                
                time.sleep(random.uniform(5, 8))
                
            except TimeoutException:
                logger.warning(f"Usuário {user_id}: Timeout durante interação")
                time.sleep(2)
            except Exception as e:
                error_msg = str(e).strip()
                if error_msg:
                    logger.warning(f"Usuário {user_id}: Erro durante interação - {error_msg}")
                else:
                    logger.warning(f"Usuário {user_id}: Erro durante interação - Possível timeout")
                time.sleep(2)
        
        logger.info(f"Usuário {user_id}: Simulação concluída com sucesso (Total de interações: {interaction_count})")
        log_memory_status(user_id, 'End')
        
    except Exception as e:
        error_msg = str(e).strip()
        if error_msg:
            logger.error(f"Usuário {user_id}: Erro durante a simulação - {error_msg}")
        else:
            logger.error(f"Usuário {user_id}: Erro durante a simulação - Timeout ou conexão perdida")
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info(f"Usuário {user_id}: Driver fechado com sucesso")
                log_memory_status(user_id, 'After Driver Quit')
            except:
                pass
            gc.collect()

def main():
    num_users = 10
    max_workers = 5
    
    logger.info(f"Iniciando simulação com {num_users} usuários ({max_workers} simultâneos)")
    log_memory_status('MAIN', 'Start')
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = list(range(1, num_users + 1))
        random.shuffle(user_ids)
        
        results = []
        for user_id in user_ids:
            results.append(executor.submit(simulate_user_access, user_id))
            time.sleep(2)
            log_memory_status('MAIN', f'User {user_id} Started')
        
        for future in results:
            future.result()
    
    log_memory_status('MAIN', 'End')
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
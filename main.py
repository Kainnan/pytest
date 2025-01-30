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
import gc
import resource
import subprocess

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'
CONNECTION_TIME = 60
MAX_RETRIES = 3
RETRY_DELAY = 5  # Aumentado para 5 segundos
MAX_MEMORY_PERCENT = 80

def get_memory_usage():
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        'memory_mb': rusage.ru_maxrss / 1024,
        'user_cpu_time': rusage.ru_utime,
        'system_cpu_time': rusage.ru_stime
    }

def log_memory_status(user_id, stage):
    mem = get_memory_usage()
    logger.info(
        f"MEMORY [Usuário {user_id}] [{stage}] - "
        f"Uso de Memória: {mem['memory_mb']:.1f}MB | "
        f"CPU User: {mem['user_cpu_time']:.1f}s | "
        f"CPU System: {mem['system_cpu_time']:.1f}s"
    )

def cleanup_firefox(user_id):
    try:
        # Mata processos do Firefox e geckodriver
        subprocess.run(['pkill', '-f', 'firefox'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'geckodriver'], stderr=subprocess.DEVNULL)
        time.sleep(2)
        logger.info(f"Usuário {user_id}: Limpeza de processos realizada")
    except Exception as e:
        logger.warning(f"Usuário {user_id}: Erro na limpeza de processos - {str(e)}")

def create_driver(user_id):
    log_memory_status(user_id, 'Pre-Driver')
    cleanup_firefox(user_id)
    
    for attempt in range(MAX_RETRIES):
        try:
            options = FirefoxOptions()
            
            # Configurações básicas
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=800,600')
            
            # Otimizações de memória
            options.add_argument('--js-flags="--max-old-space-size=256"')
            options.add_argument('--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-extensions')
            
            if os.path.exists('/usr/bin/firefox-esr'):
                options.binary_location = '/usr/bin/firefox-esr'
            
            # Preferências otimizadas
            prefs = {
                'javascript.enabled': True,
                'dom.webdriver.enabled': False,
                'browser.cache.disk.enable': False,
                'browser.cache.memory.enable': False,
                'browser.cache.offline.enable': False,
                'network.http.use-cache': False,
                'browser.sessionstore.enabled': False,
                'browser.startup.page': 0,
                'browser.download.manager.retention': 0,
                'marionette.timeout': 60000,
                'dom.max_script_run_time': 30,
                'toolkit.startup.max_resumed_crashes': -1,
                'network.http.connection-timeout': 30,
                'dom.disable_beforeunload': True,
                'dom.disable_open_during_load': True,
                'dom.popup_maximum': 0
            }
            
            for key, value in prefs.items():
                options.set_preference(key, value)
            
            service = Service(
                executable_path=GECKODRIVER_PATH,
                log_path='/dev/null'
            )
            
            driver = webdriver.Firefox(service=service, options=options)
            time.sleep(2)  # Tempo para estabilizar
            
            log_memory_status(user_id, 'Post-Driver')
            gc.collect()
            
            return driver
            
        except Exception as e:
            error_msg = str(e).strip()
            if error_msg:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - {error_msg}")
            else:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - Timeout ou conexão perdida")
            
            cleanup_firefox(user_id)
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
                
                for i in range(min(2, len(buttons))):
                    try:
                        button = buttons[i]
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
                        interaction_count += 1
                        time.sleep(1)
                    except Exception as click_error:
                        logger.warning(f"Usuário {user_id}: Erro ao clicar no botão {i+1} - {str(click_error)}")
                
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
                cleanup_firefox(user_id)
            except:
                pass

def main():
    num_users = 6  # Começando com 6 usuários
    max_workers = 3  # 3 simultâneos
    
    logger.info(f"Iniciando simulação com {num_users} usuários ({max_workers} simultâneos)")
    log_memory_status('MAIN', 'Start')
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = list(range(1, num_users + 1))
        random.shuffle(user_ids)
        
        results = []
        for user_id in user_ids:
            results.append(executor.submit(simulate_user_access, user_id))
            time.sleep(3)  # Aumentado para 3 segundos
            log_memory_status('MAIN', f'User {user_id} Started')
        
        for future in results:
            future.result()
    
    log_memory_status('MAIN', 'End')
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
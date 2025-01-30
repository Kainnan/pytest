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
import random
import threading
import subprocess
import queue
from concurrent.futures import ThreadPoolExecutor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'
CONNECTION_TIME = 60
INITIAL_BATCH_SIZE = 3  # Começamos com 3 usuários garantidos
MAX_CONCURRENT = 3      # Máximo de 3 simultâneos
TOTAL_USERS = 50       # Total de usuários que queremos atingir
BATCH_INTERVAL = 5     # 5 segundos entre tentativas de novo batch

class BrowserManager:
    def __init__(self):
        self.active_sessions = 0
        self.lock = threading.Lock()
        self.session_queue = queue.Queue()
        
    def can_start_session(self):
        with self.lock:
            if self.active_sessions < MAX_CONCURRENT:
                self.active_sessions += 1
                return True
            return False
    
    def end_session(self):
        with self.lock:
            self.active_sessions -= 1
            if self.active_sessions < 0:
                self.active_sessions = 0

def cleanup_firefox():
    try:
        subprocess.run(['pkill', '-f', 'firefox'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'geckodriver'], stderr=subprocess.DEVNULL)
        time.sleep(1)
    except:
        pass

def create_driver():
    options = FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=800,600')
    
    if os.path.exists('/usr/bin/firefox-esr'):
        options.binary_location = '/usr/bin/firefox-esr'
    
    prefs = {
        'javascript.enabled': True,
        'dom.webdriver.enabled': False,
        'browser.cache.disk.enable': False,
        'browser.cache.memory.enable': False,
        'browser.sessionstore.enabled': False,
        'network.http.connection-timeout': 30,
        'dom.max_script_run_time': 20
    }
    
    for key, value in prefs.items():
        options.set_preference(key, value)
    
    service = Service(GECKODRIVER_PATH)
    return webdriver.Firefox(service=service, options=options)

def simulate_user_access(user_id, browser_manager):
    if not browser_manager.can_start_session():
        logger.info(f"Usuário {user_id}: Aguardando slot disponível")
        return False
    
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
        cleanup_firefox()  # Limpa processos antes de começar
        
        driver = create_driver()
        driver.set_page_load_timeout(30)
        
        url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
        driver.get(url)
        logger.info(f"Usuário {user_id}: Página carregada com sucesso")
        
        start_time = time.time()
        interaction_count = 0
        
        while time.time() - start_time < CONNECTION_TIME:
            try:
                # Fechar diálogo se presente
                try:
                    dialog = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.q-dialog__backdrop"))
                    )
                    if dialog.is_displayed():
                        dialog.click()
                except:
                    pass
                
                # Encontrar e clicar nos botões
                buttons = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
                )
                
                for i in range(min(2, len(buttons))):
                    driver.execute_script("arguments[0].scrollIntoView(true);", buttons[i])
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", buttons[i])
                    logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
                    interaction_count += 1
                    time.sleep(1)
                
                time.sleep(random.uniform(5, 8))
                
            except Exception as e:
                logger.warning(f"Usuário {user_id}: Erro durante interação - {str(e)}")
                if "without establishing a connection" in str(e):
                    break
                time.sleep(2)
        
        logger.info(f"Usuário {user_id}: Simulação concluída com sucesso (Total de interações: {interaction_count})")
        return True
        
    except Exception as e:
        logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
        return False
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info(f"Usuário {user_id}: Driver fechado com sucesso")
            except:
                pass
        browser_manager.end_session()
        cleanup_firefox()  # Limpa processos ao finalizar

def process_user_batch(user_ids, browser_manager):
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        futures = []
        for user_id in user_ids:
            future = executor.submit(simulate_user_access, user_id, browser_manager)
            futures.append(future)
        
        # Aguardar conclusão
        for future in futures:
            future.result()

def main():
    logger.info(f"Iniciando simulação progressiva (máximo {MAX_CONCURRENT} simultâneos)")
    browser_manager = BrowserManager()
    
    next_user_id = 1
    while next_user_id <= TOTAL_USERS:
        # Criar batch atual
        batch_size = min(INITIAL_BATCH_SIZE, TOTAL_USERS - next_user_id + 1)
        current_batch = range(next_user_id, next_user_id + batch_size)
        
        logger.info(f"Processando batch de usuários {list(current_batch)}")
        process_user_batch(current_batch, browser_manager)
        
        next_user_id += batch_size
        
        # Intervalo entre batches
        if next_user_id <= TOTAL_USERS:
            logger.info(f"Aguardando {BATCH_INTERVAL} segundos antes do próximo batch")
            time.sleep(BATCH_INTERVAL)
    
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
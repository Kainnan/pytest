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
import threading
from functools import wraps
from queue import Queue, Empty
import atexit

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

def with_retry(max_attempts=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(RETRY_DELAY * (attempt + 1))
            return None
        return wrapper
    return decorator

class DriverPool:
    def __init__(self, pool_size):
        self.pool_size = pool_size
        self.available_drivers = Queue()
        self.active_drivers = set()
        self.lock = threading.Lock()
        self.initialized = False
    
    def _create_driver_options(self):
        options = FirefoxOptions()
        
        # Configurações básicas
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--single-process')
        options.add_argument('--disable-features=site-per-process')
        options.add_argument('--window-size=800,600')
        
        # Otimizações de memória
        options.add_argument('--js-flags="--max-old-space-size=256"')
        options.add_argument('--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies')
        
        if os.path.exists('/usr/bin/firefox-esr'):
            options.binary_location = '/usr/bin/firefox-esr'
        
        # Preferências críticas para escala
        prefs = {
            'javascript.enabled': True,
            'dom.webdriver.enabled': False,
            'browser.cache.disk.enable': False,
            'browser.cache.memory.enable': False,
            'browser.cache.offline.enable': False,
            'network.http.use-cache': False,
            'browser.sessionstore.enabled': False,
            'browser.sessionstore.max_tabs_undo': 0,
            'browser.sessionstore.max_windows_undo': 0,
            'browser.sessionhistory.max_entries': 1,
            'browser.sessionhistory.max_total_viewers': 0,
            'browser.cache.memory.capacity': 2048,
            'browser.cache.memory.max_entry_size': 512,
            'marionette.timeout': 60000,
            'dom.max_script_run_time': 30
        }
        
        for key, value in prefs.items():
            options.set_preference(key, value)
        
        return options
    
    @with_retry(max_attempts=3)
    def _create_new_driver(self):
        options = self._create_driver_options()
        service = Service(
            executable_path=GECKODRIVER_PATH,
            log_path='/dev/null'
        )
        driver = webdriver.Firefox(service=service, options=options)
        return driver
    
    def initialize_pool(self):
        if self.initialized:
            return
            
        logger.info(f"Inicializando pool com {self.pool_size} drivers")
        for _ in range(self.pool_size):
            try:
                driver = self._create_new_driver()
                if driver:
                    self.available_drivers.put(driver)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Erro ao criar driver para pool: {str(e)}")
        
        self.initialized = True
        logger.info(f"Pool inicializado com {self.available_drivers.qsize()} drivers")
    
    def get_driver(self, timeout=30):
        try:
            driver = self.available_drivers.get(timeout=timeout)
            with self.lock:
                self.active_drivers.add(driver)
            return driver
        except Empty:
            driver = self._create_new_driver()
            if driver:
                with self.lock:
                    self.active_drivers.add(driver)
            return driver
    
    def return_driver(self, driver):
        with self.lock:
            if driver in self.active_drivers:
                self.active_drivers.remove(driver)
                try:
                    driver.get("about:blank")
                    self.available_drivers.put(driver)
                except:
                    self._safely_quit_driver(driver)
    
    def _safely_quit_driver(self, driver):
        try:
            driver.quit()
        except:
            pass
    
    def cleanup(self):
        logger.info("Limpando pool de drivers")
        while not self.available_drivers.empty():
            driver = self.available_drivers.get()
            self._safely_quit_driver(driver)
        
        with self.lock:
            for driver in list(self.active_drivers):
                self._safely_quit_driver(driver)
            self.active_drivers.clear()

class UserSimulator:
    def __init__(self, driver_pool):
        self.driver_pool = driver_pool
    
    def simulate_user_access(self, user_id):
        driver = None
        try:
            logger.info(f"Usuário {user_id}: Iniciando simulação")
            log_memory_status(user_id, 'Start')
            
            driver = self.driver_pool.get_driver()
            if not driver:
                logger.error(f"Usuário {user_id}: Não foi possível obter um driver")
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
                    if attempt == MAX_RETRIES - 1:
                        raise
                    time.sleep(RETRY_DELAY)
            
            start_time = time.time()
            interaction_count = 0
            
            while time.time() - start_time < CONNECTION_TIME:
                try:
                    # Fechar diálogo se presente
                    try:
                        dialog_backdrop = driver.find_element(By.CSS_SELECTOR, "div.q-dialog__backdrop")
                        if dialog_backdrop.is_displayed():
                            dialog_backdrop.click()
                            time.sleep(1)
                    except:
                        pass
                    
                    # Interagir com botões
                    wait = WebDriverWait(driver, 10)
                    buttons = wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
                    )
                    
                    for i in range(min(2, len(buttons))):
                        button = buttons[i]
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
                        interaction_count += 1
                        time.sleep(1)
                    
                    time.sleep(random.uniform(5, 8))
                    
                except Exception as e:
                    logger.warning(f"Usuário {user_id}: Erro durante interação - {str(e)}")
                    time.sleep(2)
            
            logger.info(f"Usuário {user_id}: Simulação concluída com sucesso (Total de interações: {interaction_count})")
            
        except Exception as e:
            logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
        
        finally:
            if driver:
                self.driver_pool.return_driver(driver)
                logger.info(f"Usuário {user_id}: Driver devolvido ao pool")

def process_users_in_chunks(total_users, chunk_size, simulator):
    for i in range(0, total_users, chunk_size):
        chunk = range(i + 1, min(i + chunk_size + 1, total_users + 1))
        logger.info(f"Processando chunk de usuários {list(chunk)}")
        
        with ThreadPoolExecutor(max_workers=chunk_size) as executor:
            executor.map(simulator.simulate_user_access, chunk)
        
        time.sleep(5)  # Intervalo entre chunks

def main():
    total_users = 20  # Total de usuários
    chunk_size = 10   # Tamanho do chunk (usuários simultâneos)
    pool_size = chunk_size + 2  # Alguns drivers extras no pool
    
    logger.info(f"Iniciando simulação com {total_users} usuários (chunks de {chunk_size})")
    log_memory_status('MAIN', 'Start')
    
    # Criar e inicializar pool
    driver_pool = DriverPool(pool_size)
    driver_pool.initialize_pool()
    
    # Registrar limpeza ao finalizar
    atexit.register(driver_pool.cleanup)
    
    # Criar simulador
    simulator = UserSimulator(driver_pool)
    
    try:
        # Processar usuários em chunks
        process_users_in_chunks(total_users, chunk_size, simulator)
    finally:
        # Limpar recursos
        driver_pool.cleanup()
    
    log_memory_status('MAIN', 'End')
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
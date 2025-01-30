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
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

# Configuração avançada de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configurações otimizadas
GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'
FIREFOX_BIN = '/usr/bin/firefox-esr'
TARGET_CONCURRENT_USERS = 100
MAX_RETRIES = 3
BASE_DELAY = 0.1
RESOURCE_MONITOR_INTERVAL = 5

class ResourceMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.memory_threshold = 80  # %
        self.cpu_threshold = 85     # %
        
    def run(self):
        while self.running:
            mem = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent()
            
            if mem > self.memory_threshold or cpu > self.cpu_threshold:
                logger.warning(f"Recursos críticos! Memória: {mem}%, CPU: {cpu}%")
                self.adjust_concurrency()
                
            time.sleep(RESOURCE_MONITOR_INTERVAL)
    
    def adjust_concurrency(self):
        current_load = psutil.cpu_percent()
        if current_load > 80:
            BrowserManager.adjust_max_concurrent(-5)
        elif current_load < 30:
            BrowserManager.adjust_max_concurrent(5)

class BrowserManager:
    _max_concurrent = TARGET_CONCURRENT_USERS
    _semaphore = threading.BoundedSemaphore(_max_concurrent)
    _lock = threading.Lock()
    
    @classmethod
    def adjust_max_concurrent(cls, delta):
        with cls._lock:
            new_value = max(10, min(cls._max_concurrent + delta, 150))
            if new_value != cls._max_concurrent:
                cls._max_concurrent = new_value
                cls._semaphore = threading.BoundedSemaphore(new_value)
                logger.info(f"Novo limite de concorrência: {new_value}")

    @classmethod
    def acquire_session(cls):
        return cls._semaphore.acquire(blocking=True, timeout=30)
    
    @classmethod
    def release_session(cls):
        try:
            cls._semaphore.release()
        except ValueError:
            pass

def create_optimized_driver(user_id):
    try:
        options = FirefoxOptions()
        options.binary = FIREFOX_BIN
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument(f'--profile=/tmp/ff_profile_{user_id}')
        
        # Configurações de desempenho
        prefs = {
            'browser.sessionstore.resume_from_crash': False,
            'browser.sessionstore.max_resumed_crashes': 0,
            'dom.ipc.processCount': 2,
            'browser.tabs.remote.autostart': False,
            'layers.acceleration.disabled': True,
            'javascript.options.mem.max': 256000000,
            'javascript.options.mem.gc_high_frequency_heap_growth_max': 3,
            'network.http.max-connections-per-server': 10,
            'browser.cache.memory.enable': False,
            'browser.cache.disk.enable': False,
            'browser.sessionhistory.max_entries': 2
        }
        
        for key, value in prefs.items():
            options.set_preference(key, value)
        
        service = Service(
            executable_path=GECKODRIVER_PATH,
            service_args=['--marionette-port', '2828'],
            log_path=f"/tmp/geckodriver_{user_id}.log"
        )
        
        driver = webdriver.Firefox(
            service=service,
            options=options,
            service_log_path=None
        )
        
        driver.set_page_load_timeout(25)
        driver.set_script_timeout(20)
        return driver
    
    except Exception as e:
        logger.error(f"Falha crítica ao criar driver: {str(e)}")
        raise

def user_simulation(user_id):
    logger.info(f"Usuário {user_id}: Iniciando sessão")
    driver = None
    
    try:
        if not BrowserManager.acquire_session():
            logger.warning(f"Usuário {user_id}: Timeout ao adquirir sessão")
            return False

        for attempt in range(MAX_RETRIES):
            try:
                driver = create_optimized_driver(user_id)
                driver.get("https://gli-bcrash.eu-f2.bananaprovider.com/demo")
                
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.btn--bet"))
                )
                logger.info(f"Usuário {user_id}: Página carregada com sucesso")

                # Simulação de interação otimizada
                start_time = time.time()
                while time.time() - start_time < random.randint(45, 60):
                    try:
                        buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn--bet")[:2]
                        for btn in buttons:
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(random.uniform(0.1, 0.5))
                        
                        time.sleep(random.expovariate(1/3))
                        
                        if random.random() < 0.15:
                            driver.refresh()
                            time.sleep(2)
                            
                    except Exception as e:
                        logger.warning(f"Usuário {user_id}: Erro na interação - {str(e)}")
                        if "crash" in str(e).lower() or "disconnect" in str(e).lower():
                            break
                
                driver.quit()
                logger.info(f"Usuário {user_id}: Sessão concluída com sucesso")
                return True

            except (WebDriverException, TimeoutException) as e:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt+1} falhou - {type(e).__name__}")
                if driver:
                    try:
                        driver.service.process.kill()
                    except:
                        pass
                time.sleep(BASE_DELAY * (2 ** attempt))
                
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass

        logger.error(f"Usuário {user_id}: Todas as tentativas falharam")
        return False

    finally:
        BrowserManager.release_session()
        try:
            subprocess.run(
                f"pkill -f 'firefox.*{user_id}'", 
                shell=True, 
                stderr=subprocess.DEVNULL
            )
        except:
            pass

def run_load_test():
    monitor = ResourceMonitor()
    monitor.start()
    
    with ThreadPoolExecutor(max_workers=TARGET_CONCURRENT_USERS * 2) as executor:
        futures = {
            executor.submit(user_simulation, user_id): user_id 
            for user_id in range(1, TARGET_CONCURRENT_USERS + 1)
        }
        
        for future in as_completed(futures):
            user_id = futures[future]
            try:
                result = future.result()
                if not result:
                    logger.warning(f"Usuário {user_id}: Falha na execução")
            except Exception as e:
                logger.error(f"Usuário {user_id}: Erro não tratado - {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Iniciando teste de carga em larga escala")
        run_load_test()
        logger.info("Teste de carga concluído")
    except KeyboardInterrupt:
        logger.info("Interrupção recebida, encerrando...")
    finally:
        subprocess.run(["pkill", "-f", "geckodriver"])
        subprocess.run(["pkill", "-f", "firefox"])
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import time
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import subprocess
from threading import Lock

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'
driver_lock = Lock()
MAX_RETRIES = 3
RETRY_DELAY = 2

def cleanup_firefox():
    try:
        subprocess.run(['pkill', 'firefox'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', 'geckodriver'], stderr=subprocess.DEVNULL)
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Erro ao limpar processos: {str(e)}")

def create_driver(user_id):
    with driver_lock:
        try:
            cleanup_firefox()
            
            options = FirefoxOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            
            # Configurações de memória
            options.add_argument('--memory-pressure-off')
            options.add_argument('--disable-features=PreloadMediaEngagementData,MediaEngagementBypassAutoplayPolicies')
            
            if os.path.exists('/usr/bin/firefox-esr'):
                options.binary_location = '/usr/bin/firefox-esr'
            
            options.set_preference('javascript.enabled', True)
            options.set_preference('dom.webdriver.enabled', False)
            options.set_preference('useAutomationExtension', False)
            options.set_preference('browser.cache.disk.enable', False)
            options.set_preference('browser.cache.memory.enable', False)
            options.set_preference('browser.cache.offline.enable', False)
            options.set_preference('network.http.use-cache', False)
            
            service = Service(
                executable_path=GECKODRIVER_PATH,
                log_path='/dev/null'
            )
            
            driver = webdriver.Firefox(
                service=service,
                options=options
            )
            
            return driver
        except Exception as e:
            logger.error(f"Erro ao criar driver para usuário {user_id}: {str(e)}")
            return None

def simulate_user_access(user_id):
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
        
        for attempt in range(MAX_RETRIES):
            driver = create_driver(user_id)
            if driver:
                break
            logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou")
            time.sleep(RETRY_DELAY)
        
        if not driver:
            logger.error(f"Usuário {user_id}: Falha ao criar driver após {MAX_RETRIES} tentativas")
            return
            
        driver.set_page_load_timeout(30)
        
        # Acessar URL
        url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)
                logger.info(f"Usuário {user_id}: Página carregada com sucesso")
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} falhou")
                time.sleep(RETRY_DELAY)
        
        time.sleep(5)
        
        # Fechar diálogo
        try:
            dialog_backdrop = driver.find_element(By.CSS_SELECTOR, "div.q-dialog__backdrop")
            if dialog_backdrop.is_displayed():
                dialog_backdrop.click()
                time.sleep(1)
        except:
            pass
        
        # Interagir com botões
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
        )
        
        for i in range(min(2, len(buttons))):
            try:
                button = buttons[i]
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)
                
                driver.execute_script("""
                    var elements = document.getElementsByClassName('q-dialog__backdrop');
                    for(var i=0; i<elements.length; i++){
                        elements[i].style.display='none';
                    }
                """)
                
                driver.execute_script("arguments[0].click();", button)
                logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
                time.sleep(1)
            except Exception as click_error:
                logger.warning(f"Usuário {user_id}: Erro ao clicar no botão {i+1} - {str(click_error)}")
        
        time.sleep(5)
        logger.info(f"Usuário {user_id}: Simulação concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
    
    finally:
        if driver:
            try:
                driver.quit()
                logger.info(f"Usuário {user_id}: Driver fechado com sucesso")
            except:
                pass
            cleanup_firefox()

def main():
    # Configuração inicial mais conservadora
    num_users = 5  # Reduzido para 5 usuários
    max_workers = 2  # Reduzido para 2 workers
    
    logger.info(f"Iniciando simulação com {num_users} usuários e {max_workers} workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = range(1, num_users + 1)
        executor.map(simulate_user_access, user_ids)
    
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
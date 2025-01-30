from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
from concurrent.futures import ThreadPoolExecutor
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_driver():
    options = FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Configurar localização do binário do Firefox
    if os.path.exists('/usr/bin/firefox-esr'):
        options.binary_location = '/usr/bin/firefox-esr'
    
    # Configurar preferências específicas
    options.set_preference('javascript.enabled', True)
    options.set_preference('dom.webdriver.enabled', False)
    options.set_preference('useAutomationExtension', False)
    
    service = Service(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)

def simulate_user_access(user_id):
    driver = None
    try:
        driver = create_driver()
        driver.set_page_load_timeout(30)
        
        logger.info(f"Usuário {user_id}: Iniciando navegador")
        
        # Resto do seu código permanece o mesmo
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
                driver.get(url)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente...")
                time.sleep(2)
        
        # ... resto do código continua igual ...
        
    except Exception as e:
        logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def main():
    num_users = 1000
    max_workers = 500
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = range(1, num_users + 1)
        executor.map(simulate_user_access, user_ids)

if __name__ == "__main__":
    main()
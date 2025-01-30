from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import time
import logging
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GECKODRIVER_PATH = '/opt/geckodriver/geckodriver'

def create_driver():
    options = FirefoxOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--width=1920')
    options.add_argument('--height=1080')
    
    if os.path.exists('/usr/bin/firefox-esr'):
        options.binary_location = '/usr/bin/firefox-esr'
    
    options.set_preference('javascript.enabled', True)
    options.set_preference('dom.webdriver.enabled', False)
    
    service = Service(GECKODRIVER_PATH)
    return webdriver.Firefox(service=service, options=options)

def simulate_user_access(user_id):
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
        driver = create_driver()
        
        url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
        driver.get(url)
        logger.info(f"Usuário {user_id}: Página carregada com sucesso")
        
        time.sleep(5)
        
        try:
            dialog_backdrop = driver.find_element(By.CSS_SELECTOR, "div.q-dialog__backdrop")
            if dialog_backdrop.is_displayed():
                dialog_backdrop.click()
                time.sleep(1)
        except:
            pass
        
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
        )
        
        for i in range(min(2, len(buttons))):
            button = buttons[i]
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", button)
            logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
            time.sleep(1)
        
        time.sleep(5)
        logger.info(f"Usuário {user_id}: Simulação concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
    
    finally:
        if driver:
            driver.quit()
            logger.info(f"Usuário {user_id}: Driver fechado com sucesso")

def main():
    num_users = 2  # Começar com apenas 2 usuários para teste
    
    logger.info(f"Iniciando simulação com {num_users} usuários")
    
    # Executar usuários sequencialmente
    for user_id in range(1, num_users + 1):
        simulate_user_access(user_id)
    
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
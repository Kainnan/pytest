from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import WebDriverException
import time
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import random

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

def create_driver(user_id):
    for attempt in range(MAX_RETRIES):
        try:
            options = FirefoxOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            options.add_argument('--disable-gpu')
            
            if os.path.exists('/usr/bin/firefox-esr'):
                options.binary_location = '/usr/bin/firefox-esr'
            
            options.set_preference('javascript.enabled', True)
            options.set_preference('dom.webdriver.enabled', False)
            options.set_preference('browser.cache.disk.enable', False)
            options.set_preference('browser.cache.memory.enable', False)
            
            service = Service(
                executable_path=GECKODRIVER_PATH,
                log_path='/dev/null'
            )
            
            driver = webdriver.Firefox(service=service, options=options)
            return driver
            
        except Exception as e:
            logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - {str(e)}")
            time.sleep(RETRY_DELAY)
    
    return None

def is_driver_alive(driver):
    try:
        # Tenta executar um comando simples para verificar se o driver ainda está responsivo
        driver.current_url
        return True
    except:
        return False

def click_button_safely(driver, button, user_id, button_num):
    try:
        if not is_driver_alive(driver):
            raise WebDriverException("Driver não está mais responsivo")
            
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", button)
        logger.info(f"Usuário {user_id}: Clicou no botão {button_num}")
        return True
    except Exception as e:
        logger.warning(f"Usuário {user_id}: Erro ao clicar no botão {button_num} - {str(e)}")
        return False

def simulate_user_access(user_id):
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
        driver = create_driver(user_id)
        
        if not driver:
            logger.error(f"Usuário {user_id}: Falha ao criar driver após {MAX_RETRIES} tentativas")
            return
        
        # Configurar tempo limite de página
        driver.set_page_load_timeout(30)
        
        # Carregar página inicial
        url = "https://gli-bcrash.eu-f2.bananaprovider.com/demo"
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(url)
                logger.info(f"Usuário {user_id}: Página carregada com sucesso")
                break
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de carregar página falhou")
                time.sleep(RETRY_DELAY)
        
        # Loop principal de interação
        start_time = time.time()
        while time.time() - start_time < CONNECTION_TIME:
            if not is_driver_alive(driver):
                logger.error(f"Usuário {user_id}: Driver perdeu a conexão")
                break
                
            try:
                # Tentar fechar diálogo
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
                
                success = False
                for i in range(min(2, len(buttons))):
                    if click_button_safely(driver, buttons[i], user_id, i+1):
                        success = True
                        time.sleep(1)
                
                if not success:
                    logger.warning(f"Usuário {user_id}: Nenhum botão foi clicado com sucesso")
                    continue
                
                # Espera entre interações
                time.sleep(random.uniform(5, 8))
                
            except Exception as e:
                logger.warning(f"Usuário {user_id}: Erro durante interação - {str(e)}")
                time.sleep(2)
        
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

def main():
    num_users = 8  # Reduzido de 10 para 8
    max_workers = 4  # Reduzido de 5 para 4
    
    logger.info(f"Iniciando simulação com {num_users} usuários ({max_workers} simultâneos)")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = list(range(1, num_users + 1))
        random.shuffle(user_ids)
        executor.map(simulate_user_access, user_ids)
    
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
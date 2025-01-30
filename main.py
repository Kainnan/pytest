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
            
            # Configurações básicas do headless
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            # Otimizações de memória e performance
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-save-password-bubble')
            options.add_argument('--disable-single-click-autofill')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-web-security')
            options.add_argument('--ignore-certificate-errors')
            
            if os.path.exists('/usr/bin/firefox-esr'):
                options.binary_location = '/usr/bin/firefox-esr'
            
            # Preferências do Firefox para otimização
            options.set_preference('javascript.enabled', True)
            options.set_preference('dom.webdriver.enabled', False)
            options.set_preference('browser.cache.disk.enable', False)
            options.set_preference('browser.cache.memory.enable', False)
            options.set_preference('network.http.connection-timeout', 30)
            options.set_preference('dom.max_script_run_time', 20)
            
            # Desabilitar recursos visuais não necessários
            options.set_preference('browser.tabs.remote.autostart', False)
            options.set_preference('browser.tabs.remote.autostart.2', False)
            options.set_preference('browser.sessionstore.interval', 60000)
            options.set_preference('image.animation_mode', 'none')
            options.set_preference('media.autoplay.default', 5)
            options.set_preference('media.autoplay.enabled', False)
            options.set_preference('media.hardware-video-decoding.enabled', False)
            options.set_preference('media.webspeech.synth.enabled', False)
            options.set_preference('webgl.disabled', True)
            options.set_preference('dom.ipc.plugins.enabled', False)
            
            # Configurar tamanho mínimo da janela
            options.add_argument('--window-size=800,600')
            
            service = Service(
                executable_path=GECKODRIVER_PATH,
                log_path='/dev/null'
            )
            
            driver = webdriver.Firefox(service=service, options=options)
            return driver
            
        except Exception as e:
            error_msg = str(e).strip()
            if error_msg:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - {error_msg}")
            else:
                logger.warning(f"Usuário {user_id}: Tentativa {attempt + 1} de criar driver falhou - Timeout ou conexão perdida")
            time.sleep(RETRY_DELAY)
    
    return None

def is_driver_alive(driver):
    try:
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
        
        try:
            driver.execute_script("arguments[0].click();", button)
        except:
            button.click()
            
        logger.info(f"Usuário {user_id}: Clicou no botão {button_num}")
        return True
    except Exception as e:
        error_msg = str(e).strip()
        if error_msg:
            logger.warning(f"Usuário {user_id}: Erro ao clicar no botão {button_num} - {error_msg}")
        else:
            logger.warning(f"Usuário {user_id}: Timeout ao clicar no botão {button_num}")
        return False

def simulate_user_access(user_id):
    driver = None
    try:
        logger.info(f"Usuário {user_id}: Iniciando simulação")
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
            if not is_driver_alive(driver):
                logger.error(f"Usuário {user_id}: Driver perdeu a conexão")
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
            except:
                pass

def main():
    num_users = 15  # Aumentado para 15 usuários
    max_workers = 8  # Aumentado para 8 simultâneos
    
    logger.info(f"Iniciando simulação com {num_users} usuários ({max_workers} simultâneos)")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        user_ids = list(range(1, num_users + 1))
        random.shuffle(user_ids)
        executor.map(simulate_user_access, user_ids)
    
    logger.info("Simulação concluída")

if __name__ == "__main__":
    main()
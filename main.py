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

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Configurar opções do Firefox
options = FirefoxOptions()
options.add_argument('--headless')  # Rodar sem interface gráfica

# Inicializar o WebDriver usando o WebDriverManager
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service, options=options)

def simulate_user_access(user_id):
    try:
        # Configurar opções do Firefox
        options = FirefoxOptions()
        options.add_argument('--headless')
        options.set_preference("javascript.enabled", True)
        
        # Inicializar o navegador Firefox
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(30)
        
        logger.info(f"Usuário {user_id}: Iniciando navegador")
        
        # Acessar a URL com retry
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
        
        # Esperar 15 segundos
        time.sleep(18)
        
        # Tentar fechar o diálogo se estiver presente
        try:
            dialog_backdrop = driver.find_element(By.CSS_SELECTOR, "div.q-dialog__backdrop")
            if dialog_backdrop.is_displayed():
                dialog_backdrop.click()
                time.sleep(1)
        except:
            pass
        
        # Encontrar e clicar nos botões com retry
        for attempt in range(max_retries):
            try:
                # Esperar pelos botões serem clicáveis
                buttons = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button.btn--bet"))
                )
                
                for i in range(min(2, len(buttons))):
                    button = buttons[i]
                    # Tentar diferentes métodos para clicar no botão
                    try:
                        # Método 1: Scroll até o botão
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        time.sleep(0.5)
                        
                        # Método 2: Remover overlay se existir
                        driver.execute_script("""
                            var elements = document.getElementsByClassName('q-dialog__backdrop');
                            for(var i=0; i<elements.length; i++){
                                elements[i].style.display='none';
                            }
                        """)
                        
                        # Método 3: Clicar via JavaScript
                        driver.execute_script("arguments[0].click();", button)
                        logger.info(f"Usuário {user_id}: Clicou no botão {i+1}")
                    except Exception as click_error:
                        logger.warning(f"Erro ao clicar no botão {i+1}: {str(click_error)}")
                    
                    time.sleep(1)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente...")
                time.sleep(2)
        time.sleep(120)
        logger.info(f"Usuário {user_id}: Simulação concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Usuário {user_id}: Erro durante a simulação - {str(e)}")
    
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass

def main():
    # Reduzir o número de usuários simultâneos para diminuir a carga
    num_users = 1000
    max_workers = 500  # Reduzido para 5 workers simultâneos
    
    # Usar ThreadPoolExecutor para simular múltiplos usuários
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Criar lista de IDs de usuários
        user_ids = range(1, num_users + 1)
        
        # Executar simulações
        executor.map(simulate_user_access, user_ids)

if __name__ == "__main__":
    main()

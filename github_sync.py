import os
import time
from git import Repo, GitCommandError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from datetime import datetime

# Configurações - CORRIGIDAS
LOCAL_REPO_PATH = r"C:\Users\Tznnt\Desktop\US GURI"  # Pasta do repositório local
GITHUB_REPO_URL = "https://github.com/TznNt/Teste-de-automa-o.git"  # URL do repositório Git (não da página web)
FILE_TO_MONITOR = r"documento_teste.txt"  # Nome do arquivo a monitorar (deve estar na pasta do repositório)
SYNC_INTERVAL = 30  # Intervalo de verificação (segundos)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'github_sync.log')),
        logging.StreamHandler()
    ]
)

class GitSyncHandler(FileSystemEventHandler):
    def __init__(self):
        self.ensure_repository_exists()
        self.repo = Repo(LOCAL_REPO_PATH)
        self.origin = self.repo.remotes.origin
        self.last_sync = datetime.now()
        self.setup_git_config()

    def ensure_repository_exists(self):
        if not os.path.exists(LOCAL_REPO_PATH):
            os.makedirs(LOCAL_REPO_PATH, exist_ok=True)
            logging.info(f"Diretório {LOCAL_REPO_PATH} criado com sucesso.")
            
            # Inicializa o repositório Git se não existir
            if not os.path.exists(os.path.join(LOCAL_REPO_PATH, '.git')):
                Repo.init(LOCAL_REPO_PATH)
                logging.info("Repositório Git inicializado localmente.")
                
                # Adiciona remote origin se especificado
                if GITHUB_REPO_URL:
                    try:
                        repo = Repo(LOCAL_REPO_PATH)
                        repo.create_remote('origin', GITHUB_REPO_URL)
                        logging.info(f"Remote 'origin' configurado para {GITHUB_REPO_URL}")
                    except Exception as e:
                        logging.error(f"Erro ao configurar remote: {e}")

    def setup_git_config(self):
        try:
            with self.repo.config_writer() as git_config:
                git_config.set_value("user", "name", "GitHub Sync Bot")
                git_config.set_value("user", "email", "bot@example.com")
        except Exception as e:
            logging.error(f"Erro na configuração do Git: {e}")

    def on_modified(self, event):
        if not event.is_directory and os.path.basename(event.src_path) == FILE_TO_MONITOR:
            logging.info(f"Arquivo {FILE_TO_MONITOR} modificado. Sincronizando...")
            self.sync_changes()

    def sync_changes(self):
        try:
            # Verifica se há alterações para commit
            if not self.repo.index.diff(None) and not self.repo.untracked_files:
                logging.info("Nenhuma alteração detectada para commit.")
                return

            # Atualiza do remoto primeiro
            self.origin.pull(rebase=True)
            logging.info("Alterações remotas incorporadas.")

            # Adiciona todas as mudanças
            self.repo.git.add(A=True)
            
            # Faz o commit
            commit_message = f"Auto-sync em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self.repo.index.commit(commit_message)
            
            # Envia para o remoto
            self.origin.push()
            self.last_sync = datetime.now()
            logging.info("Alterações enviadas para o GitHub!")
        except GitCommandError as e:
            logging.error(f"Erro durante a sincronização: {e}")
            self.handle_sync_error(e)
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")

    def handle_sync_error(self, error):
        if "conflict" in str(error).lower():
            logging.warning("Conflito detectado. Tentando resolver...")
            try:
                self.repo.git.execute(['git', 'mergetool'])
                self.repo.git.add(update=True)
                self.repo.index.commit("Resolvendo conflitos automáticos")
                self.origin.push()
            except Exception as e:
                logging.error(f"Falha ao resolver conflitos: {e}")

def start_monitoring():
    event_handler = GitSyncHandler()
    observer = Observer()
    observer.schedule(event_handler, path=LOCAL_REPO_PATH, recursive=False)
    observer.start()
    
    logging.info(f"Monitorando alterações em {os.path.join(LOCAL_REPO_PATH, FILE_TO_MONITOR)}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    try:
        start_monitoring()
    except Exception as e:
        logging.error(f"Erro fatal: {e}")
        exit(1)
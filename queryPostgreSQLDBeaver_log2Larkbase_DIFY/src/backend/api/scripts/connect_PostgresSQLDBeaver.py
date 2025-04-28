# File: connect.py
import os
import psycopg2
from sshtunnel import SSHTunnelForwarder

# Cấu hình chung cho database
DB_CONFIG = {
    "db_name": "dify",
    "db_user": "postgres",
    "db_password": "difyai123456",
    "db_port": 5434,
}

# Cấu hình cho development (SSH tunnel)
DEV_CONFIG = {
    "ssh_host": "103.253.20.13",
    "ssh_port": 22,
    "ssh_user": "ubuntu",
    "ssh_private_key": "C:/Users/User/.ssh/id_rsa",
    "db_host": "localhost",
}

# Cấu hình cho production (kết nối trực tiếp)
PROD_CONFIG = {
    "db_host": "103.253.20.13",  # IP của database server
}

def connect_to_database():
    """
    Connect to PostgreSQL database with or without SSH Tunnel
    based on environment variable USE_SSH_TUNNEL
    """
    try:
        use_ssh = os.getenv('USE_SSH_TUNNEL', 'false').lower() == 'true'
        
        if use_ssh:
            # Development: Sử dụng SSH tunnel
            tunnel = SSHTunnelForwarder(
                (DEV_CONFIG["ssh_host"], DEV_CONFIG["ssh_port"]),
                ssh_username=DEV_CONFIG["ssh_user"],
                ssh_private_key=DEV_CONFIG["ssh_private_key"],
                remote_bind_address=(DEV_CONFIG["db_host"], DB_CONFIG["db_port"])
            )
            tunnel.start()
            print("SSH Tunnel connected!")

            connection = psycopg2.connect(
                dbname=DB_CONFIG["db_name"],
                user=DB_CONFIG["db_user"],
                password=DB_CONFIG["db_password"],
                host="127.0.0.1",
                port=tunnel.local_bind_port
            )
            print("PostgreSQL connection successful via SSH tunnel!")
            return tunnel, connection
            
        else:
            # Production: Kết nối trực tiếp
            connection = psycopg2.connect(
                dbname=DB_CONFIG["db_name"],
                user=DB_CONFIG["db_user"],
                password=DB_CONFIG["db_password"],
                host=PROD_CONFIG["db_host"],
                port=DB_CONFIG["db_port"]
            )
            print("PostgreSQL connection successful with direct connection!")
            return None, connection

    except Exception as e:
        print("An error occurred while connecting:", e)
        raise

if __name__ == "__main__":
    connect_to_database()
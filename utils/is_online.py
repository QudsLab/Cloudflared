# check the internet connection status
import socket
def is_online(host="8.8.8.8", port=53, timeout=3):
    """
    Check if the system is online by attempting to connect to a known host.
    
    Args:
        host (str): The host to connect to. Default is Google DNS (8.8.8.8).
        port (int): The port to connect to. Default is 53 (DNS).
        timeout (int): Connection timeout in seconds. Default is 3.
    
    Returns:
        bool: True if online, False otherwise.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def check_connection():
    online = False
    is_it_correct = []
    
    # first check google DNS
    is_it_correct.append(is_online(host="8.8.8.8"))
    # then check cloudflare DNS
    is_it_correct.append(is_online(host="1.1.1.1"))
    # finally check quad9 DNS
    is_it_correct.append(is_online(host="9.9.9.9"))

    # if any(is_it_correct): # if any check returned True
    #     online = True

    if all(is_it_correct): # if all checks returned True
        online = True

    return online

if __name__ == "__main__":
    if check_connection():
        print("The system is online.")
    else:
        print("The system is offline.")
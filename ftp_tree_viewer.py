import ftplib
import argparse
import os
import fnmatch

def ftp_tree(ftp, directory, indent='', recursion_depth=None, show_perms=False, show_hidden=False, error_ignore=False, only_dirs=False, world_writable=False):
    if recursion_depth is not None and recursion_depth < 1:
        return
    items = []
    try:
        ftp.cwd(directory)
        list_command = 'LIST -a' if show_hidden else 'LIST'
        ftp.retrlines(list_command, items.append)
    except ftplib.error_perm as e:
        if not error_ignore:
            print(indent + '└── Access denied for listing directory: ' + directory)
        return
    except Exception as e:
        if not error_ignore:
            print(indent + '└── Error accessing directory: ' + directory)
            print(indent + '└── ' + str(e))
        return

    items = [item.split() for item in items]
    items = sorted(items, key=lambda x: x[-1])
    last = len(items) - 1
    for index, item in enumerate(items):
        permissions, _, _, _, _, _, _, _, name = item[:9]
        if not show_hidden and name.startswith('.'):
            continue
        if only_dirs and permissions[0] != 'd':
            continue
        if world_writable and permissions[-2] != 'w':
            continue
        short_name = name.split('/')[-1]
        prefix = '└── ' if index == last else '├── '
        line = f"{prefix}{short_name}"
        if show_perms:
            line = f"{permissions} {line}"
        print(indent + line)
        if '.' not in short_name and permissions[0] == 'd' and not world_writable:
            if recursion_depth is None or recursion_depth > 1:
                new_indent = indent + ('    ' if index == last else '│   ')
                new_dir = f"{directory}/{short_name}" if directory != '/' else f"/{short_name}"
                new_depth = None if recursion_depth is None else recursion_depth - 1
                ftp_tree(ftp, new_dir, new_indent, new_depth, show_perms, show_hidden, error_ignore, only_dirs, world_writable)

def parse_host_port(host_port_str):
    if ':' in host_port_str:
        host, port = host_port_str.split(':')
        return host, int(port)
    return host_port_str, 21

def cat_file(ftp, filepath, show_perms=False, error_ignore=False):
    try:
        if show_perms:
            items = []
            ftp.cwd('/')
            ftp.retrlines('LIST ' + filepath, items.append)
            if items:
                permissions = items[0].split()[0]
                print(f"Permissions: {permissions}")
        ftp.retrlines(f"RETR {filepath}", print)
    except Exception as e:
        if not error_ignore:
            print(f"Error reading file {filepath}: {e}")

def download_files(ftp, pattern):
    base_directory = ftp.pwd()
    wildcard = os.path.basename(pattern)
    directory = os.path.dirname(pattern)

    # Change to the specified directory on the FTP server
    if directory:
        try:
            ftp.cwd(directory)
        except ftplib.error_perm:
            print(f"Permission denied for directory: {directory}")
            ftp.cwd(base_directory)
            return []
        except Exception as e:
            print(f"Error accessing directory {directory}: {e}")
            ftp.cwd(base_directory)
            return []

    items = []
    ftp.retrlines('LIST -a', lambda line: items.append(line.split()[-1]))

    # Download logic based on type
    for item in items:
        if item in ('.', '..'):
            continue  # Skip special directories

        # Determine if the item is a directory or a file
        try:
            ftp.cwd(item)  # Try to change into the directory
            ftp.cwd('..')  # Change back if successful
            item_type = 'directory'
        except ftplib.error_perm:
            item_type = 'file'

        if item_type == 'directory' and (wildcard == '*' or item == wildcard):
            local_dir = os.path.join(os.getcwd(), item)
            os.makedirs(local_dir, exist_ok=True)  # Create local directory
            download_files(ftp, os.path.join(directory, item, '*'))  # Recursively download directory contents
        elif item_type == 'file' and (wildcard == '*' or fnmatch.fnmatch(item, wildcard)):
            local_path = os.path.join(os.getcwd(), directory, item) if directory else os.path.join(os.getcwd(), item)
            with open(local_path, 'wb') as f:
                ftp.retrbinary('RETR ' + item, f.write)  # Download the file
            print(f"Downloaded {local_path}")

    ftp.cwd(base_directory)  # Reset the FTP directory to the original

def main():
    parser = argparse.ArgumentParser(description='FTP Utility Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands', required=True, metavar='COMMAND')

    parser_list = subparsers.add_parser('list', formatter_class=argparse.RawTextHelpFormatter,
                                        help='List directories in a tree-like format')
    parser_list.add_argument('-u', '--username', required=True, help='FTP username')
    parser_list.add_argument('-p', '--password', required=True, help='FTP password')
    parser_list.add_argument('host', help='FTP server IP address, optionally with port (ip:port)')
    parser_list.add_argument('-d', '--directory', default='/', help='Custom directory to list from')
    parser_list.add_argument('--perms', action='store_true', help='Show permissions of files and directories')
    parser_list.add_argument('--hidden', action='store_true', help='Show hidden files and directories')
    parser_list.add_argument('--error-ignore', action='store_true', help='Ignore and skip errors during listing')
    parser_list.add_argument('--only-dir', action='store_true', help='List only directories')
    parser_list.add_argument('--world-writable', action='store_true', help='List only world-writable files and directories')
    parser_list.add_argument('-r', '--recursion', type=int, default=None, help='Set the recursion depth (None for fully recursive, 0 for no recursion)')
    parser_list.epilog = "Examples:\n" \
                         "  Basic Usage: python ftp_tree_viewer.py list -u username -p password 192.168.1.100\n" \
                         "  Directories Only: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --only-dir\n" \
                         "  World-Writable Only: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --world-writable\n" \
                         "  With Permissions: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --perms\n" \
                         "  Custom Directory: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 -d /path/to/directory\n" \
                         "  Show Hidden Files: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --hidden\n" \
                         "  Fully Recursive: python ftp_tree_viewer.py list -u username -p password 192.168.1.100\n" \
                         "  No Recursion: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --recursion 0"

    parser_cat = subparsers.add_parser('cat', formatter_class=argparse.RawTextHelpFormatter,
                                       help='Display the contents of a file')
    parser_cat.add_argument('-u', '--username', required=True, help='FTP username')
    parser_cat.add_argument('-p', '--password', required=True, help='FTP password')
    parser_cat.add_argument('host', help='FTP server IP address, optionally with port (ip:port)')
    parser_cat.add_argument('-f', '--file', required=True, help='Path to the file to display')
    parser_cat.add_argument('--perms', action='store_true', help='Show permissions of the file')
    parser_cat.add_argument('--error-ignore', action='store_true', help='Ignore and skip errors during file display')
    parser_cat.epilog = "Examples:\n" \
                        "  Display File: python ftp_tree_viewer.py cat -u username -p password 192.168.1.100 -f /path/to/file\n" \
                        "  With Permissions: python ftp_tree_viewer.py cat -u username -p password 192.168.1.100 -f /path/to/file --perms"

    parser_get = subparsers.add_parser('get', formatter_class=argparse.RawTextHelpFormatter,
                                       help='Download files or directories from the FTP server')
    parser_get.add_argument('-u', '--username', required=True, help='FTP username')
    parser_get.add_argument('-p', '--password', required=True, help='FTP password')
    parser_get.add_argument('host', help='FTP server IP address, optionally with port (ip:port)')
    parser_get.add_argument('-f', '--file', required=True, help='File or directory to download, supports wildcards (*, path/*)')
    parser_get.epilog = "Examples:\n" \
                        "  Download Single File: python ftp_tree_viewer.py get -u username -p password 192.168.1.100 -f /path/to/file\n" \
                        "  Download Directory: python ftp_tree_viewer.py get -u username -p password 192.168.1.100 -f /path/to/directory/*\n" \
                        "  Download All: python ftp_tree_viewer.py get -u username -p password 192.168.1.100 -f *"

    args = parser.parse_args()

    host, port = parse_host_port(args.host)

    try:
        ftp = ftplib.FTP()
        ftp.connect(host=host, port=port)
        ftp.login(args.username, args.password)
        print(f"Connected to FTP at {host}:{port}")

        if args.command == 'list':
            print("Directory listing:")
            ftp_tree(ftp, args.directory, recursion_depth=args.recursion, show_perms=args.perms, show_hidden=args.hidden,
                     error_ignore=args.error_ignore, only_dirs=args.only_dir, world_writable=args.world_writable)
        elif args.command == 'cat':
            print("File content:")
            cat_file(ftp, args.file, show_perms=args.perms, error_ignore=args.error_ignore)
        elif args.command == 'get':
            print("Downloading files...")
            downloaded_files = download_files(ftp, args.file)

        ftp.quit()
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")
    except Exception as e:
        print(f"Failed to connect or login to FTP server: {e}")

if __name__ == "__main__":
    main()


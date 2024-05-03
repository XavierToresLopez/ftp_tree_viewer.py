import ftplib
import argparse

def ftp_tree(ftp, directory, indent='', show_perms=False, show_hidden=False, error_ignore=False, only_dirs=False, world_writable=False):
    """ Recursively list directories in a tree-like format with special characters and optional permissions. Filter for only directories or world-writable items if specified. """
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
            new_indent = indent + ('    ' if index == last else '│   ')
            new_dir = f"{directory}/{short_name}" if directory != '/' else f"/{short_name}"
            ftp_tree(ftp, new_dir, new_indent, show_perms, show_hidden, error_ignore, only_dirs, world_writable)

def parse_host_port(host_port_str):
    if ':' in host_port_str:
        host, port = host_port_str.split(':')
        return host, int(port)
    return host_port_str, 21

def cat_file(ftp, filepath, show_perms=False, error_ignore=False):
    """ Display the contents of a file from FTP, optionally showing permissions. """
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

def main():
    parser = argparse.ArgumentParser(description='FTP Utility Tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands', required=True, metavar='COMMAND')

    # Subparser for list command
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
    parser_list.epilog = "Examples:\n" \
                         "  Basic Usage: python ftp_tree_viewer.py list -u username -p password 192.168.1.100\n" \
                         "  Directories Only: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --only-dir\n" \
                         "  World-Writable Only: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --world-writable\n" \
                         "  With Permissions: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --perms\n" \
                         "  Custom Directory: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 -d /path/to/directory\n" \
                         "  Show Hidden Files: python ftp_tree_viewer.py list -u username -p password 192.168.1.100 --hidden"

    # Subparser for cat command
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

    args = parser.parse_args()

    host, port = parse_host_port(args.host)

    try:
        ftp = ftplib.FTP()
        ftp.connect(host=host, port=port)
        ftp.login(args.username, args.password)
        print(f"Connected to FTP at {host}:{port}")

        if args.command == 'list':
            print("Directory listing:")
            ftp_tree(ftp, args.directory, show_perms=args.perms, show_hidden=args.hidden,
                     error_ignore=args.error_ignore, only_dirs=args.only_dir, world_writable=args.world_writable)
        elif args.command == 'cat':
            print("File content:")
            cat_file(ftp, args.file, show_perms=args.perms, error_ignore=args.error_ignore)

        ftp.quit()
    except Exception as e:
        print(f"Failed to connect or login to FTP server: {e}")

if __name__ == "__main__":
    main()


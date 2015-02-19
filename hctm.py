
import os
import shutil
import zipfile
import argparse
import subprocess


def is_hexchat_running():
    proc = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    output, _ = proc.communicate()
    lines = [l.split(None, 4) for l in
             output.decode('ascii', 'replace').splitlines()]
    for pid, _, _, cmdname in lines:
        if cmdname.lower() == 'hexchat':
            return True
    return False


def get_installed_themes(themes_dir):
    if not os.path.exists(themes_dir):
        return []
    filenames = ((os.path.join(themes_dir, fn), fn) for fn in os.listdir(themes_dir))
    dirnames = [fn for fn in filenames if os.path.isdir(fn[0])]
    dirnames.sort(key=lambda e: e[1].lower())
    return dirnames


def load_meta_data(meta_file):
    metadata = {}
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as fp:
            lines = list(fp)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue
            if '=' not in line:
                continue
            key, _, value = line.partition('=')
            metadata[key.strip()] = value.strip()
    return metadata


def show_themes(config):
    themes = get_installed_themes(config['themes_dir'])
    if not themes:
        print('No themes installed.')
        return
    meta = load_meta_data(config['meta_file'])

    current = meta.get('current', '\033[33mNone\033[0m')
    print('\nCurrently used theme: {}'.format(current))

    print('\nInstalled themes:')
    for path, name in themes:
        print('  * {}'.format(name))
    print()
    print('Use -u/--use THEME to use the specified theme.')


def use_theme(config, theme):
    if is_hexchat_running():
        print('\033[31mHexChat is still running.')
        print('You have to close HexChat before any changes to the '
              'themes can be applied.\033[0m')
        return


def remove_theme(config, theme):
    pass


def install_theme(config, fileobj):
    theme_name = os.path.basename(fileobj.name)
    if theme_name.lower().endswith(('.hct', '.zip')):
        theme_name = theme_name[:-4]

    target_dir = os.path.join(config['themes_dir'], theme_name)
    if os.path.exists(target_dir):
        answer = input('A theme with the name {} already exists. '
                       'Overwrite? (y/N): '.format(theme_name)).lower().strip()
        if answer != 'y':
            print('Aborting.')
            return
        to_remove = []
        shutil.rmtree(target_dir)

    os.makedirs(target_dir)
    z = zipfile.ZipFile(fileobj, 'r')
    result = z.testzip()
    if result is not None:
        print('Bad Zip File: {}'.format(result))
    z.extractall(target_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HexChat Theme Manager.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-u', '--use', dest='use', action='store',
        required=False, metavar='THEME', type=str,
        help='Use the specified theme.')
    group.add_argument(
        '-r', '--remove', dest='remove', action='store',
        required=False, metavar='THEME', type=str,
        help='Remove the specified theme completely.')
    group.add_argument(
        '-i', '--install', dest='install', action='store',
        required=False, metavar='FILE', type=argparse.FileType('rb'),
        help='Install a new theme (.hct or .zip file)')
    args = parser.parse_args()

    config = {}
    config['config_dir'] = os.path.join(os.environ['HOME'], '.config', 'hexchat')
    config['themes_dir'] = os.path.join(config['config_dir'], 'themes')
    config['meta_file'] = os.path.join(config['themes_dir'], '.theme')
    config['allowed_files'] = {'pevents.conf', 'colors.conf'}

    if args.install is None and args.use is None and args.remove is None:
        show_themes(config)
    elif args.install is None and args.use is None:
        remove_theme(config, args.remove)
    elif args.install is None and args.remove is None:
        use_theme(config, args.use)
    else:
        install_theme(config, args.install)

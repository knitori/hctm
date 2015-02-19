
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
    """Return a list of tuples (path_to_dir, dirname) for each
    theme under ~/.config/hexchat/themes/"""

    if not os.path.exists(themes_dir):
        return []
    filenames = ((os.path.join(themes_dir, fn), fn) for fn
                 in os.listdir(themes_dir))
    dirnames = [fn for fn in filenames if os.path.isdir(fn[0])]
    dirnames.sort(key=lambda e: e[1].lower())
    return dirnames


def load_meta_data(meta_file):
    """The meta file is a simple 'key = value' per line config.
    Return a dictionary of those values."""

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


def write_meta_data(meta_file, metadata):
    with open(meta_file, 'w', encoding='utf-8') as fp:
        for key, value in sorted(metadata.items()):
            fp.write('{} = {}\n'.format(key, value))


def show_themes(config):
    themes = get_installed_themes(config['themes_dir'])
    if not themes:
        print('No themes installed.')
        return
    meta = load_meta_data(config['meta_file'])
    current = meta.get('current', '')
    print('\nInstalled themes:')
    current_in_list = False
    for path, name in themes:
        if current.lower() == name.lower():
            print('  * {}'.format(name))
            current_in_list = True
        else:
            print('    {}'.format(name))
    if not current_in_list:
        # theme folder deleted, but theme is still active
        print('  ! {}'.format(current))
    print()
    print('Use -u/--use THEME to use the specified theme.')


def use_theme(config, theme):
    """Enable a theme that's installed in the hexchat themes folder."""

    themes = get_installed_themes(config['themes_dir'])
    for themes_dir, themes_name in themes:
        if themes_name.lower() == theme.lower():
            # themes_dir and themes_name will be available
            # outside the for-loop
            break
    else:
        print('No such theme {!r}.'.format(theme))
        return

    meta = load_meta_data(config['meta_file'])
    current_theme = meta.get('current', '')
    if current_theme.lower() == theme.lower():
        print('The theme {!r} is already in use.'.format(current_theme))
        return

    if is_hexchat_running():
        print('HexChat is still running.')
        print('You have to close HexChat before any changes to the '
              'themes can be applied.')
        return

    to_copy = []

    print('Activating theme {!r}'.format(themes_name))
    for filename in os.listdir(themes_dir):
        if filename in config['allowed_files']:
            theme_file = os.path.join(themes_dir, filename)
            target_file = os.path.join(config['config_dir'], filename)
            to_copy.append((theme_file, target_file, filename,
                            os.path.exists(target_file)))
    replace_count = sum(1 for p in to_copy if p[-1])
    if replace_count:
        print()
        for src, dst, fn, exists in to_copy:
            if exists:
                print('{}'.format(dst))
        print()
        answer = input('The above files will be replace by the new files. '
                       'Continue? (y/N)').lower().strip()
        if answer != 'y':
            print('Aborted.')
            return
    for src, dst, fn, exists in to_copy:
        shutil.copyfile(src, dst)
    meta['current'] = themes_name
    write_meta_data(config['meta_file'], meta)
    print('Finished.')


def remove_theme(config, theme):
    """Remove a theme from the hexchat themes folder."""

    if is_hexchat_running():
        print('HexChat is still running.')
        print('You have to close HexChat before any changes to the '
              'themes can be applied.')
        return


def install_theme(config, fileobj):
    """Copy zip file content into the hexchat themes folder."""

    theme_name = os.path.basename(fileobj.name)
    if theme_name.lower().endswith(('.hct', '.zip')):
        theme_name = theme_name[:-4]

    target_dir = os.path.join(config['themes_dir'], theme_name)
    if os.path.exists(target_dir):
        answer = input('A theme with the name {} already exists. '
                       'Replace? (y/N): '.format(theme_name)).lower().strip()
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
    config['config_dir'] = os.path.join(
        os.environ['HOME'], '.config', 'hexchat')
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

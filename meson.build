project(
    'bgm_tv_wiki',
    'c',
    default_options: [
        'c_std=c11',
        'buildtype=release',
        'debug=false',
        'python.allow_limited_api=false',
    ],
    meson_version: '>= 1.5.0',
)

allow_limited_api = get_option('python.allow_limited_api')
py_limited_api = allow_limited_api ? '3.10' : ''

py = import('python').find_installation(pure: false)

py.install_sources(
    'src/bgm_tv_wiki/__init__.py',
    'src/bgm_tv_wiki/py.typed',
    subdir: 'bgm_tv_wiki',
)

cython = find_program('cython')

cython_args = ['-3']

cython_gen = generator(
    cython,
    output: ['@BASENAME@.c'],
    arguments: ['@INPUT@', '--output-file', '@OUTPUT0@'] + cython_args,
)

parser_c = cython_gen.process(
    'src/bgm_tv_wiki/__init__.py',
    preserve_path_from: meson.current_source_dir(),
)

out = py.extension_module(
    '__init__',
    parser_c,
    subdir: 'bgm_tv_wiki',
    install: true,
    dependencies: py.dependency(),
    limited_api: py_limited_api,
)

# support for in-tree build
# # will target will copy binary extension back to source directory
custom_target(
    'copy extension back to source tree',
    input: out,
    output: 'copy',
    depends: out,
    command: [
        'cp',
        out.full_path(),
        join_paths(meson.project_source_root(), 'src/bgm_tv_wiki/'),
    ],
    build_by_default: false,
)

project(
    'bgm_tv_wiki',
    'c',
    default_options: [
        'c_std=c11',
        'buildtype=release',
        'debug=false',
    ],
    meson_version: '>= 1.5.0',
)

py = import('python').find_installation(pure: false)

cython = find_program('cython')

cython_gen = generator(
    cython,
    output: ['@BASENAME@.c'],
    arguments: ['-3', '@INPUT@', '--output-file', '@OUTPUT0@'],
)

ast_c = cython_gen.process(
    'src/bgm_tv_wiki/ast.py',
    preserve_path_from: meson.current_source_dir(),
)

py.extension_module(
    'ast',
    ast_c,
    subdir: 'bgm_tv_wiki',
    dependencies: py.dependency(),
)

"""Test how gradients are drawn."""

from ..testing_utils import assert_no_logs


@assert_no_logs
def test_linear_gradients_1(assert_pixels):
    assert_pixels('''
        _____
        _____
        _____
        BBBBB
        BBBBB
        RRRRR
        RRRRR
        RRRRR
        RRRRR
    ''', '''<style>@page { size: 5px 9px; background: linear-gradient(
      white, white 3px, blue 0, blue 5px, red 0, red
    )''')


@assert_no_logs
def test_linear_gradients_2(assert_pixels):
    assert_pixels('''
        _____
        _____
        _____
        BBBBB
        BBBBB
        RRRRR
        RRRRR
        RRRRR
        RRRRR
    ''', '''<style>@page { size: 5px 9px; background: linear-gradient(
      white 3px, blue 0, blue 5px, red 0
    )''')


@assert_no_logs
def test_linear_gradients_3(assert_pixels):
    assert_pixels('''
        ___BBrrrr
        ___BBrrrr
        ___BBrrrr
        ___BBrrrr
        ___BBrrrr
    ''', '''<style>@page { size: 9px 5px; background: linear-gradient(
      to right, white 3px, blue 0, blue 5px, red 0
    )''')


@assert_no_logs
def test_linear_gradients_4(assert_pixels):
    assert_pixels('''
        BBBBBBrrrr
        BBBBBBrrrr
        BBBBBBrrrr
        BBBBBBrrrr
        BBBBBBrrrr
    ''', '''<style>@page { size: 10px 5px; background: linear-gradient(
      to right, blue 5px, blue 6px, red 6px, red 9px
    )''')


@assert_no_logs
def test_linear_gradients_5(assert_pixels):
    assert_pixels('''
        rBrrrBrrrB
        rBrrrBrrrB
        rBrrrBrrrB
        rBrrrBrrrB
        rBrrrBrrrB
    ''', '''
      <style>@page { size: 10px 5px; background: repeating-linear-gradient(
      to right, blue 50%, blue 60%, red 60%, red 90%
    )''')


@assert_no_logs
def test_linear_gradients_6(assert_pixels):
    assert_pixels('''
        BBBrrrrrr
        BBBrrrrrr
        BBBrrrrrr
        BBBrrrrrr
        BBBrrrrrr
    ''', '''<style>@page { size: 9px 5px; background: linear-gradient(
      to right, blue 3px, blue 3px, red 3px, red 3px
    )''')


@assert_no_logs
def test_linear_gradients_7(assert_pixels):
    assert_pixels('''
        hhhhhhhhh
        hhhhhhhhh
        hhhhhhhhh
        hhhhhhhhh
        hhhhhhhhh
    ''', '''<style>@page { size: 9px 5px; background:
    repeating-linear-gradient(
      to right, black 3px, black 3px, #800080 3px, #800080 3px
    )''')


@assert_no_logs
def test_linear_gradients_8(assert_pixels):
    assert_pixels('''
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
    ''', '''<style>@page { size: 9px 5px; background:
      repeating-linear-gradient(to right, blue 3px)''')


@assert_no_logs
def test_linear_gradients_9(assert_pixels):
    assert_pixels('''
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
    ''', '''<style>@page { size: 9px 5px; background:
      repeating-linear-gradient(45deg, blue 3px)''')


@assert_no_logs
def test_linear_gradients_10(assert_pixels):
    assert_pixels('''
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
    ''', '''<style>@page { size: 9px 5px; background: linear-gradient(
      45deg, blue 3px, red 3px, red 3px, blue 3px
    )''')


@assert_no_logs
def test_linear_gradients_11(assert_pixels):
    assert_pixels('''
        BBBrBBBBB
        BBBrBBBBB
        BBBrBBBBB
        BBBrBBBBB
        BBBrBBBBB
    ''', '''<style>@page { size: 9px 5px; background: linear-gradient(
      to right, blue 3px, red 3px, red 4px, blue 4px
    )''')


@assert_no_logs
def test_linear_gradients_12(assert_pixels):
    assert_pixels('''
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
        BBBBBBBBB
    ''', '''<style>@page { size: 9px 5px; background:
      repeating-linear-gradient(to right, red 3px, blue 3px, blue 4px, red 4px
    )''')


@assert_no_logs
def test_linear_gradients_13(assert_pixels):
    assert_pixels('''
        _____
        _____
        _____
        SSSSS
        SSSSS
        RRRRR
        RRRRR
        RRRRR
        RRRRR
    ''', '''<style>@page { size: 5px 9px; background: linear-gradient(
      white, white 3px, rgba(255, 0, 0, 0.751) 0, rgba(255, 0, 0, 0.751) 5px,
      red 0, red
    )''')


@assert_no_logs
def test_radial_gradients_1(assert_pixels):
    assert_pixels('''
        BBBBBB
        BBBBBB
        BBBBBB
        BBBBBB
        BBBBBB
        BBBBBB
    ''', '''<style>@page { size: 6px; background:
      radial-gradient(red -30%, blue -10%)''')


@assert_no_logs
def test_radial_gradients_2(assert_pixels):
    assert_pixels('''
        RRRRRR
        RRRRRR
        RRRRRR
        RRRRRR
        RRRRRR
        RRRRRR
    ''', '''<style>@page { size: 6px; background:
      radial-gradient(red 110%, blue 130%)''')


@assert_no_logs
def test_radial_gradients_3(assert_pixels):
    assert_pixels('''
        BzzzzzzzzB
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzRRzzzz
        zzzzRRzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        BzzzzzzzzB
    ''', '''<style>@page { size: 10px 16px; background:
      radial-gradient(red 20%, blue 80%)''')


@assert_no_logs
def test_radial_gradients_4(assert_pixels):
    assert_pixels('''
        BzzzzzzzzB
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzRRzzzz
        zzzzRRzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        BzzzzzzzzB
    ''', '''<style>@page { size: 10px 16px; background:
      radial-gradient(red 50%, blue 50%)''')


@assert_no_logs
def test_radial_gradients_5(assert_pixels):
    assert_pixels('''
        SzzzzzzzzS
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzRRzzzz
        zzzzRRzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        zzzzzzzzzz
        SzzzzzzzzS
    ''', '''<style>@page { size: 10px 16px; background:
      radial-gradient(red 50%, rgba(255, 0, 0, 0.751) 50%)''')

"""Test how SVG text is drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_text_fill(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" font-family="weasyprint" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_combining_character(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 20px 20px }
        svg { display: block }
      </style>
      <svg width="20px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="15" font-family="weasyprint" font-size="16" fill="blue">
          é
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 20px 20px }
        svg { display: block }
      </style>
      <svg width="20px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="15" font-family="weasyprint" font-size="16" fill="blue">
          é
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_ligature(assert_pixels):
    assert_pixels('''
        BBB_________________
        BBB_________________
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" font-family="weasyprint" font-size="2" fill="blue">
          liga
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_combining_character(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 24px 20px }
        svg { display: block }
      </style>
      <svg width="24px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 10" y="15" font-family="weasyprint" font-size="16"
              fill="blue">
          éa
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 24px 20px }
        svg { display: block }
      </style>
      <svg width="24px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 10" y="15" font-family="weasyprint" font-size="16"
              fill="blue">
          éa
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_combining_dx_dy(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 24px 32px }
        svg { display: block }
      </style>
      <svg width="24px" height="32px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 100 10" y="16" dx="0 6 4" dy="0 -8 8"
              font-family="weasyprint" font-size="16" fill="blue">
          éA
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 24px 32px }
        svg { display: block }
      </style>
      <svg width="24px" height="32px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 10" y="16" dx="0 10" dy="0 0"
              font-family="weasyprint" font-size="16" fill="blue">
          éA
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_combining_final_rotate(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 24px 20px }
        svg { display: block }
      </style>
      <svg width="24px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="3 100 13" y="15" rotate="0 180"
              font-family="weasyprint" font-size="10" fill="blue">
          éA
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 24px 20px }
        svg { display: block }
      </style>
      <svg width="24px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="3 13" y="15" rotate="0 180"
              font-family="weasyprint" font-size="10" fill="blue">
          éA
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_ligature(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 3 6 9" y="3" font-family="weasyprint" font-size="4"
              fill="blue">
          liga
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="3" font-family="weasyprint" font-size="4" fill="blue">
          liga
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_rtl(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 90px 24px }
        svg { display: block }
      </style>
      <svg width="90px" height="24px" xmlns="http://www.w3.org/2000/svg">
        <text x="70 60 50 40" y="20" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="18" fill="blue">
          שלום
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 90px 24px }
        svg { display: block }
      </style>
      <svg width="90px" height="24px" xmlns="http://www.w3.org/2000/svg">
        <text x="40" y="20" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="18" fill="blue">ם</text>
        <text x="50" y="20" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="18" fill="blue">ו</text>
        <text x="60" y="20" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="18" fill="blue">ל</text>
        <text x="70" y="20" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="18" fill="blue">ש</text>
      </svg>
    ''')

@assert_no_logs
def test_text_positioned_rtl_european_numbers(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 100px 34px }
        svg { display: block }
      </style>
      <svg width="100px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="76 52 64 44 20 32 0" y="25" direction="rtl"
              text-anchor="end" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">س12-34م</text>
      </svg>
    ''', '''
      <style>
        @page { size: 100px 34px }
        svg { display: block }
      </style>
      <svg width="100px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="24" fill="blue">م</text>
        <text x="20 32" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">34</text>
        <text x="44" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">-</text>
        <text x="52 64" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">12</text>
        <text x="76" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="24" fill="blue">س</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_rtl_arabic_numbers(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 100px 34px }
        svg { display: block }
      </style>
      <svg width="100px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="76 20 32 44 52 64 0" y="25" direction="rtl"
              text-anchor="end" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">س١٢/٣٤م</text>
      </svg>
    ''', '''
      <style>
        @page { size: 100px 34px }
        svg { display: block }
      </style>
      <svg width="100px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="24" fill="blue">م</text>
        <text x="20 32" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">١٢</text>
        <text x="44" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">/</text>
        <text x="52 64" y="25" font-family="weasyprint-amiri-arabic" font-size="24"
              fill="blue">٣٤</text>
        <text x="76" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="24" fill="blue">س</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_arabic_lam_alef_shaping(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 80px 50px }
        svg { display: block }
      </style>
      <svg width="80px" height="50px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="36" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="28"
              fill="blue">سلام</text>
      </svg>
    ''', '''
      <style>
        @page { size: 80px 50px }
        svg { display: block }
      </style>
      <svg width="80px" height="50px" xmlns="http://www.w3.org/2000/svg">
        <text x="32.0048828125 25.14453125 12.65625 0" y="36"
              direction="rtl"
              text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="28"
              fill="blue">سلام</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_persian_joining(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 120px 50px }
        svg { display: block }
      </style>
      <svg width="120px" height="50px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="36" direction="rtl" text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="28"
              fill="blue">میخواهم</text>
      </svg>
    ''', '''
      <style>
        @page { size: 120px 50px }
        svg { display: block }
      </style>
      <svg width="120px" height="50px" xmlns="http://www.w3.org/2000/svg">
        <text x="66.9208984375 60.0888671875 43.0087890625 33.3486328125
                 27.2724609375 14.6162109375 0"
              y="36" direction="rtl"
              text-anchor="end"
              font-family="weasyprint-amiri-arabic" font-size="28"
              fill="blue">میخواهم</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_rtl_neutral_punctuation(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 104px 34px }
        svg { display: block }
      </style>
      <svg width="104px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="84 72 60 52 44 12 20 28 0" y="25" direction="rtl"
              text-anchor="end" font-family="weasyprint-noto-hebrew" font-size="22"
              fill="blue">אבג (abc)</text>
      </svg>
    ''', '''
      <style>
        @page { size: 104px 34px }
        svg { display: block }
      </style>
      <svg width="104px" height="34px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="25" font-family="weasyprint-noto-hebrew" font-size="22"
              fill="blue">(</text>
        <text x="12 20 28" y="25" font-family="weasyprint-noto-hebrew" font-size="22"
              fill="blue">abc</text>
        <text x="44" y="25" font-family="weasyprint-noto-hebrew" font-size="22"
              fill="blue">)</text>
        <text x="60" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="22" fill="blue">ג</text>
        <text x="72" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="22" fill="blue">ב</text>
        <text x="84" y="25" direction="rtl" text-anchor="end"
              font-family="weasyprint-noto-hebrew" font-size="22" fill="blue">א</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_boundary_neutral_joiner(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 40px 20px }
        svg { display: block }
      </style>
      <svg width="40px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 100" y="15" font-family="weasyprint" font-size="16"
              fill="blue">A&#x200D;B</text>
      </svg>
    ''', '''
      <style>
        @page { size: 40px 20px }
        svg { display: block }
      </style>
      <svg width="40px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="15" font-family="weasyprint" font-size="16"
              fill="blue">AB</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_explicit_bidi_formatting_controls(
        assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 50px 20px }
        svg { display: block }
      </style>
      <svg width="50px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 8 16 24" y="15" font-family="weasyprint"
              font-size="16" fill="blue">A&#x202A;BC&#x202C;D</text>
      </svg>
    ''', '''
      <style>
        @page { size: 50px 20px }
        svg { display: block }
      </style>
      <svg width="50px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 8 16 24" y="15" font-family="weasyprint" font-size="16"
              fill="blue">ABCD</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_bidi_control_characters_are_not_addressable(
        assert_same_renderings):
    text = (
        'A&#x061C;&#x200E;&#x200F;B&#x202A;&#x202C;C&#x202B;&#x202C;D'
        '&#x202D;&#x202C;E&#x202E;&#x202C;F&#x2066;&#x2069;G'
        '&#x2067;&#x2069;H&#x2068;&#x2069;IJK')
    assert_same_renderings(f'''
      <style>
        @page {{ size: 104px 20px }}
        svg {{ display: block }}
      </style>
      <svg width="104px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 8 16 24 32 40 48 56 64 72 80" y="15"
              font-family="weasyprint" font-size="16" fill="blue">{text}</text>
      </svg>
    ''', '''
      <style>
        @page { size: 104px 20px }
        svg { display: block }
      </style>
      <svg width="104px" height="20px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 8 16 24 32 40 48 56 64 72 80" y="15"
              font-family="weasyprint" font-size="16" fill="blue">ABCDEFGHIJK</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_bidi_controls_with_position_lists(
        assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 70px 32px }
        svg { display: block }
      </style>
      <svg width="70px" height="32px" xmlns="http://www.w3.org/2000/svg">
        <text x="4 16 30 44" y="22 19 22 19" dx="0 1 2 3"
              dy="0 -1 1 0" rotate="0 10 -10 0"
              font-family="weasyprint" font-size="16" fill="blue">
          A&#x200E;B&#x200F;C&#x061C;D
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 70px 32px }
        svg { display: block }
      </style>
      <svg width="70px" height="32px" xmlns="http://www.w3.org/2000/svg">
        <text x="4 16 30 44" y="22 19 22 19" dx="0 1 2 3"
              dy="0 -1 1 0" rotate="0 10 -10 0"
              font-family="weasyprint" font-size="16" fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_bidi_isolate_controls(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 70px 24px }
        svg { display: block }
      </style>
      <svg width="70px" height="24px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 8 20 32 44 56" y="19" font-family="weasyprint-noto-hebrew"
              font-size="18" fill="blue">A&#x2067;שלום&#x2069;B</text>
      </svg>
    ''', '''
      <style>
        @page { size: 70px 24px }
        svg { display: block }
      </style>
      <svg width="70px" height="24px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">A</text>
        <text x="44" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">ם</text>
        <text x="32" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">ו</text>
        <text x="20" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">ל</text>
        <text x="8" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">ש</text>
        <text x="56" y="19" font-family="weasyprint-noto-hebrew" font-size="18"
              fill="blue">B</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_cjk(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 110px 36px }
        svg { display: block }
      </style>
      <svg width="110px" height="36px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 24 48 72" y="28"
              font-family="weasyprint-noto-cjk"
              font-size="26" fill="blue">
          漢日本한
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 110px 36px }
        svg { display: block }
      </style>
      <svg width="110px" height="36px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="28"
              font-family="weasyprint-noto-cjk"
              font-size="26" fill="blue">漢</text>
        <text x="24" y="28"
              font-family="weasyprint-noto-cjk"
              font-size="26" fill="blue">日</text>
        <text x="48" y="28"
              font-family="weasyprint-noto-cjk"
              font-size="26" fill="blue">本</text>
        <text x="72" y="28"
              font-family="weasyprint-noto-cjk"
              font-size="26" fill="blue">한</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_korean_jamo(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 18 36" y="30" font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">
          한
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="30" font-family="weasyprint-noto-cjk" font-size="28"
              fill="blue">
          한
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_devanagari_vowel_sign(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 18" y="30" font-family="weasyprint-noto-devanagari" font-size="28"
              fill="blue">
          कि
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="30" font-family="weasyprint-noto-devanagari" font-size="28"
              fill="blue">
          कि
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_devanagari_conjunct(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 18 36 54" y="30"
              font-family="weasyprint-noto-devanagari" font-size="28" fill="blue">
          क्षि
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 90px 42px }
        svg { display: block }
      </style>
      <svg width="90px" height="42px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="30" font-family="weasyprint-noto-devanagari"
              font-size="28" fill="blue">
          क्षि
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_korean_jamo_word(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 120 120 24 120 120" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">
          한글
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 24" y="32" font-family="weasyprint-noto-cjk" font-size="28"
              fill="blue">
          한글
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_devanagari_word(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 120 28 120 120 120" y="32"
              font-family="weasyprint-noto-devanagari" font-size="28" fill="blue">
          किक्षि
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 400 28 400 400 400" y="32"
              font-family="weasyprint-noto-devanagari" font-size="28" fill="blue">
          किक्षि
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_sanskrit_word(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 120 24 120 120 120 48" y="32"
              font-family="weasyprint-noto-devanagari"
              font-size="28" fill="blue">
          संस्कृत
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="32" font-family="weasyprint-noto-devanagari"
              font-size="28" fill="blue">सं</text>
        <text x="24" y="32" font-family="weasyprint-noto-devanagari"
              font-size="28" fill="blue">स्कृ</text>
        <text x="48" y="32" font-family="weasyprint-noto-devanagari"
              font-size="28" fill="blue">त</text>
      </svg>
    ''')


@assert_no_logs
def test_text_positioned_cjk_word(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 24 48 72 96" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">
          中文日本어
        </text>
      </svg>
    ''', '''
      <style>
        @page { size: 150px 44px }
        svg { display: block }
      </style>
      <svg width="150px" height="44px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">中</text>
        <text x="24" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">文</text>
        <text x="48" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">日</text>
        <text x="72" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">本</text>
        <text x="96" y="32"
              font-family="weasyprint-noto-cjk"
              font-size="28" fill="blue">어</text>
      </svg>
    ''')


@assert_no_logs
def test_text_vertical_rl_inline_size(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 100px 300px }
        svg { display: block }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="100" height="300" viewBox="0 0 100 300">
        <text x="62.5" y="25" inline-size="200"
              style="font: 25px weasyprint-noto-cjk; inline-size: 200px;
                     writing-mode: vertical-rl;"
              fill="blue">テキストは１０文字後に折り返されます。</text>
      </svg>
    ''', '''
      <style>
        @page { size: 100px 300px }
        svg { display: block }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="100" height="300" viewBox="0 0 100 300">
        <text x="62.5" y="25"
              style="font: 25px weasyprint-noto-cjk;
                     writing-mode: vertical-rl;"
              fill="blue">テキストは１０文</text>
        <text x="37.5" y="25"
              style="font: 25px weasyprint-noto-cjk;
                     writing-mode: vertical-rl;"
              fill="blue">字後に折り返され</text>
        <text x="12.5" y="25"
              style="font: 25px weasyprint-noto-cjk;
                     writing-mode: vertical-rl;"
              fill="blue">ます。</text>
      </svg>
    ''')


@assert_no_logs
def test_text_rtl_inline_size(assert_same_renderings):
    assert_same_renderings('''
      <style>
        @page { size: 300px 100px }
        svg { display: block }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="300" height="100" viewBox="0 0 300 100">
        <text x="250" y="30"
              style="font: 20px weasyprint-amiri-arabic; inline-size: 200px;
                     direction: rtl;"
              fill="blue">هذا النص يلتف في 200 بكسل.</text>
      </svg>
    ''', '''
      <style>
        @page { size: 300px 100px }
        svg { display: block }
      </style>
      <svg xmlns="http://www.w3.org/2000/svg"
           width="300" height="100" viewBox="0 0 300 100">
        <text x="250" y="30"
              style="font: 20px weasyprint-amiri-arabic; direction: rtl;"
              fill="blue">هذا النص يلتف في 200</text>
        <text x="250" y="65.16015625"
              style="font: 20px weasyprint-amiri-arabic; direction: rtl;"
              fill="blue">بكسل.</text>
      </svg>
    ''')


@assert_no_logs
def test_text_stroke(assert_pixels):
    assert_pixels('''
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
        _BBBBBBBBBBBB_______
    ''', '''
      <style>
        @page { font-size: 1px; size: 20em 4em }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="2.5" font-family="weasyprint" font-size="2"
              fill="transparent" stroke="blue" stroke-width="1ex">
          A B C
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_x(assert_pixels):
    assert_pixels('''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 4 7" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_y(assert_pixels):
    assert_pixels('''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
    ''', '''
      <style>
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="9 9 4 9 4" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_xy(assert_pixels):
    assert_pixels('''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
    ''', '''
      <style>
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0 10" y="9 4 9 4" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDE
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dx(assert_pixels):
    assert_pixels('''
        BB__BB_BBBB_________
        BB__BB_BBBB_________
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text dx="0 2 1" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABCD
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dy(assert_pixels):
    assert_pixels('''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
        BBBBBBBBBB_____BBBBB__________
    ''', '''
      <style>
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" dy="9 0 -5 5 -5" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_dx_dy(assert_pixels):
    assert_pixels('''
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        __________BBBBB_____BBBBBBBBBB
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
        BBBBB__________BBBBB__________
    ''', '''
      <style>
        @page { size: 30px 10px }
        svg { display: block }
      </style>
      <svg width="30px" height="10px" xmlns="http://www.w3.org/2000/svg">
        <text dx="0 5" dy="9 -5 5 -5" font-family="weasyprint" font-size="5"
              fill="blue">
          ABCDE
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_start(assert_pixels):
    assert_pixels('''
        __BBBBBB____________
        __BBBBBB____________
        ____BBBBBB__________
        ____BBBBBB__________
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABC
        </text>
        <text x="4" y="3.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="start">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="middle">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="18" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue" text-anchor="end">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_direction_rtl_anchor_start(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" direction="rtl"
           xmlns="http://www.w3.org/2000/svg">
        <text x="18" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_direction_rtl_anchor_end(assert_pixels):
    assert_pixels('''
        __BBBBBB____________
        __BBBBBB____________
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2"
              fill="blue" direction="rtl" text-anchor="end">
          ABC
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_unicode_bidi_override(assert_pixels):
    assert_pixels('''
        BBBBBBBBBB__________
        BBBBBBBBBB__________
        BBBBBBBBBB__________
        BBBBBBBBBB__________
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="3" font-family="weasyprint" font-size="4"
              fill="blue" direction="rtl" unicode-bidi="bidi-override">
          liga
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="0" y="1.5">ABC DEF</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_middle(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="10" y="1.5" text-anchor="middle">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_end(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="18" y="1.5" text-anchor="end">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle_tspan(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="middle">
          <tspan x="10" y="1.5">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end_tspan(assert_pixels):
    assert_pixels('''
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="end">
          <tspan x="18" y="1.5">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle_tspan_head_tail(assert_pixels):
    assert_pixels('''
        ____BBBBRRRRRRBB____
        ____BBBBRRRRRRBB____
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="middle">
          AA<tspan fill="red">ABC</tspan>A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_end_tspan_head_tail(assert_pixels):
    assert_pixels('''
        ______BBBBRRRRRRBB__
        ______BBBBRRRRRRBB__
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="18" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
              text-anchor="end">
          AA<tspan fill="red">ABC</tspan>A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_anchor_middle_end_tspan(assert_pixels):
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
        ____________BBBBBB__
        ____________BBBBBB__
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" fill="blue">
          <tspan x="10" y="1.5" text-anchor="middle">ABC</tspan>
          <tspan x="18" y="3.5" text-anchor="end">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_tspan_anchor_non_text(assert_pixels):
    # Regression test for #2375.
    assert_pixels('''
        _______BBBBBB_______
        _______BBBBBB_______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" text-anchor="end"
           xmlns="http://www.w3.org/2000/svg">
        <text x="10" y="10" font-family="weasyprint" font-size="2" text-anchor="start">
          <tspan x="10" y="1.5" text-anchor="middle" fill="blue">ABC</tspan>
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_rotate(assert_pixels):
    assert_pixels('''
        __RR__RR__RR________
        __RR__RR__RR________
        BB__BB__BB__________
        BB__BB__BB__________
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red"
          letter-spacing="2">abc</text>
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="blue"
          rotate="180" letter-spacing="2">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_text_length(assert_pixels):
    assert_pixels('''
        __RRRRRR____________
        __RRRRRR____________
        __BB__BB__BB________
        __BB__BB__BB________
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red">
          abc
        </text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          textLength="10">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_length_adjust_glyphs_only(assert_pixels):
    assert_pixels('''
        __RRRRRR____________
        __RRRRRR____________
        __BBBBBBBBBBBB______
        __BBBBBBBBBBBB______
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red">
          abc
        </text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          textLength="12" lengthAdjust="spacingAndGlyphs">abc</text>
      </svg>
    ''')


@assert_no_logs
def test_text_font_face(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <style>
            @font-face {
              font-family: "SVGFont";
              src: url(weasyprint.otf);
            }
          </style>
        </defs>
        <text x="0" y="1.5" font-family="SVGFont" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_font_face_css(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <style>
            @font-face {
              font-family: "SVGFont";
              src: url(weasyprint.otf);
            }
            text { font-family: "SVGFont" }
          </style>
        </defs>
        <text x="0" y="1.5" font-size="2" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''')


@assert_no_logs
def test_text_length_adjust_spacing_and_glyphs(assert_pixels):
    assert_pixels('''
        __RR_RR_RR__________
        __RR_RR_RR__________
        __BBBB__BBBB__BBBB__
        __BBBB__BBBB__BBBB__
    ''', '''
      <style>
        @page { size: 20px 4px }
        svg { display: block }
      </style>
      <svg width="20px" height="4px" xmlns="http://www.w3.org/2000/svg">
        <text x="2" y="1.5" font-family="weasyprint" font-size="2" fill="red"
          letter-spacing="1">abc</text>
        <text x="2" y="3.5" font-family="weasyprint" font-size="2" fill="blue"
          letter-spacing="1" textLength="16" lengthAdjust="spacingAndGlyphs">
          abc
        </text>
      </svg>
    ''')


@assert_no_logs
def test_font_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" style="font: 2px 'weasyprint'" fill="blue">
          ABC DEF
        </text>
      </svg>
    ''',
    )


@assert_no_logs
def test_font_shorthand_inheritance_from_parent(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g style="font: 2px weasyprint">
          <text x="0" y="1.5" fill="blue" font="bad">
            <tspan>ABC DEF</tspan>
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_explicit_properties_override_parent_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font="  28px Times New Roman  ">
          <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_font_shorthand_overrides_explicit_parent_properties(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="18px" font-family="weasyprint">
          <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_child_font_shorthand_overrides_parent_shorthand(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font="   34px    sans   ">
          <text x="0" y="1.5" style="font: 2px    weasyprint" fill="blue">
            ABC DEF
          </text>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_mixed_explicit_and_shorthand_across_levels(assert_pixels):
    assert_pixels('''
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    ''', '''
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="40px" font-family="sans-serif">
          <g style="font: 30px sans">
            <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
              ABC DEF
            </text>
          </g>
        </g>
      </svg>
    ''',
    )


@assert_no_logs
def test_text_fill_opacity(assert_pixels):
    # Regression text for #2665.
    assert_pixels('''
        ______
        _ssss_
        _ssss_
        _ssss_
        _ssss_
        ______
    ''', '''
      <style>
        @page { size: 6px 6px }
        svg { display: block }
      </style>
      <svg width="6px" height="6px" xmlns="http://www.w3.org/2000/svg">
        <text x="1" y="4" font="4px weasyprint" fill="red" opacity="0.5">
          A
        </text>
      </svg>
    ''')


@assert_no_logs
def test_emoji_text_svg(assert_pixels):
    # Regression text for #2683.
    assert_pixels('''
        zzzzz
        zzzzz
        zzzzz
        zzzzz
        zzzzz
    ''', '''
      <style>
        @page { size: 5px 5px }
        svg { display: block }
      </style>
      <svg viewBox="0 0 5 5">
        <text>🚀</text>
      </svg>
    ''')

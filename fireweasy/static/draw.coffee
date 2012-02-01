window.FireWeasy = (($) ->
    draw_box = (box, x=0, y=0) ->
        # box.position_x and box.position_y are from the page corner,
        # but left and top in CSS with 'position: absolute' refer
        # to the padding area of the closest positionned ancesteor.
        # So we track that with x and y.
        style = box.style
        css =
            position: 'absolute'
            left: box.position_x - x
            top: box.position_y - y
            width: box.width
            height: box.height
        for name in ['font-size', 'font-family', 'font-weight',
                     'text-decoration', 'background-color',
                     'background-repeat']
            css[name] = style[name.replace('-', '_')]
        if style.background_image
            css['background-image'] = 'url(data:image/png;base64,' +
                style.background_image + ')'
        css['background-position'] = style.background_position.join(' ')
        for side in ['top', 'bottom', 'left', 'right']
            css['margin-' + side] = style['margin_' + side]
            css['padding-' + side] = style['padding_' + side]
            for prop in ['width', 'style', 'color']
                css['border-' + side + '-' + prop] =
                    style['border_' + side + '_' + prop]
        if box.image
            div = $('<img>').attr('src', 'data:image/png;base64,' + box.image)
        else
            div = $('<div></div>')
        div.css(css)
        if box.text
            div.text(box.text)
        x = box.position_x + box.margin_left + box.border_left_width
        y = box.position_y + box.margin_top + box.border_top_width
        for child in box.children or []
            div.append(draw_box(child, x, y))
        div

    draw_page = (page) -> $('<section></section>').append(draw_box(page)).css(
            position: 'relative'
            width: page.outer_width + 'px'
            height: page.outer_height + 'px'
            margin: '20px'
            'box-shadow': '3px 3px 3px 3px #666')

    draw: (document, container) ->
        container.append($.map(document.pages, draw_page)...)
)(jQuery)

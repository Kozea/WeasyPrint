window.FireWeasy = (($) ->
    draw_box = (box, page) ->
        div = $('<div></div>').appendTo(page).css(
            position: 'absolute'
            top: box.position_y
            left: box.position_x
            width: box.width
            height: box.height
        )
        if box.text
            div.text(box.text)
        for child in box.children or []
            draw_box(child, page)

    draw_page = (page) ->
        section = $('<section></section>').css(
            position: 'relative'
            width: page.outer_width + 'px'
            height: page.outer_height + 'px'
            margin: '20px'
            'box-shadow': '3px 3px 3px 3px #888')
        draw_box(page, section)
        section

    draw: (document, container) ->
        container.append.apply(container, $.map(document.pages, draw_page))
)(jQuery)

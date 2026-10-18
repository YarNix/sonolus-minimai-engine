

from sonolus.script.globals import level_data
from sonolus.script.sprite import RenderMode, Sprite, SpriteGroup, StandardSprite, skin, sprite, sprite_group


@skin
class BaseSkin:
    render_mode: RenderMode = RenderMode.LIGHTWEIGHT

    # Simple sprites for debug drawing purposes
    white_square: Sprite = sprite("White Square")
    white_outline: Sprite = sprite("White Outline")

    normal_line: Sprite = sprite("Mai Normal Line")
    break_line: Sprite = sprite("Mai Break Line")
    each_line: Sprite = sprite("Mai Each Line")
    star_line: Sprite = sprite("Mai Star Line")
    each_ring_line: SpriteGroup = sprite_group(f"Mai Each Ring Line {i}" for i in range(1, 5))
    
    normal_note: Sprite = sprite("Mai Normal Note")
    break_note: Sprite = sprite("Mai Break Note")
    break_note_light: Sprite = sprite("Mai Break Note Light")
    break_note_dark: Sprite = sprite("Mai Break Note Dark")
    each_note: Sprite = sprite("Mai Each Note")
    normal_note_ex_outline: Sprite = sprite("Mai Normal Note Ex Outline")
    break_note_ex_outline: Sprite = sprite("Mai Break Note Ex Outline")
    each_note_ex_outline: Sprite = sprite("Mai Each Note Ex Outline")

    normal_star: Sprite = sprite("Mai Normal Star")
    break_star: Sprite = sprite("Mai Break Star")
    each_star: Sprite = sprite("Mai Each Star")
    normal_star_ex_outline: Sprite = sprite("Mai Normal Star Ex Outline")
    break_star_ex_outline: Sprite = sprite("Mai Break Star Ex Outline")
    each_star_ex_outline: Sprite = sprite("Mai Each Star Ex Outline")

    double_star: Sprite = sprite("Mai Double Star")
    break_double_star: Sprite = sprite("Mai Break Double Star")
    each_double_star: Sprite = sprite("Mai Each Double Star")
    double_star_ex_outline: Sprite = sprite("Mai Double Star Ex Outline")
    break_double_star_ex_outline: Sprite = sprite("Mai Break Double Star Ex Outline")
    each_double_star_ex_outline: Sprite = sprite("Mai Each Double Star Ex Outline")

    normal_touch_point: Sprite = sprite("Mai Normal Touch Point")
    break_touch_point: Sprite = sprite("Mai Break Touch Point")
    each_touch_point: Sprite = sprite("Mai Each Touch Point")

    normal_touch_fan: Sprite = sprite("Mai Normal Touch Fan")
    break_touch_fan: Sprite = sprite("Mai Break Touch Fan")
    each_touch_fan: Sprite = sprite("Mai Each Touch Fan")

    normal_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Normal Touch {i} Overlap Border" for i in range(2, 4))
    break_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Break Touch {i} Overlap Border" for i in range(2, 4))
    each_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Each Touch {i} Overlap Border" for i in range(2, 4))

    touch_just_border: Sprite = sprite("Mai Touch Just Border")

    slide_path: Sprite = sprite("Mai Slide Path")
    break_slide_path: Sprite = sprite("Mai Break Slide Path")
    each_slide_path: Sprite = sprite("Mai Each Slide Path")

    wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Wifi Slide Path {i}" for i in range(1, 12))
    break_wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Break Wifi Slide Path {i}" for i in range(1, 12))
    each_wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Each Wifi Slide Path {i}" for i in range(1, 12))

    hold_note: Sprite = sprite("Mai Hold Note")
    hold_note_off: Sprite = sprite("Mai Hold Note Off")
    hold_note_on: Sprite = sprite("Mai Hold Note On")
    break_hold_note: Sprite = sprite("Mai Break Hold Note")
    break_hold_note_on: Sprite = sprite("Mai Break Hold Note On")
    each_hold_note: Sprite = sprite("Mai Each Hold Note")
    each_hold_note_on: Sprite = sprite("Mai Each Hold Note On")

    ring: Sprite = sprite("Mai Ring")
    sensor_outline: Sprite = sprite("Mai Sensor Outline")
    

@level_data
class ActiveSkin:
    white_square: Sprite
    white_outline: Sprite

    normal_line: Sprite
    break_line: Sprite
    each_line: Sprite
    star_line: Sprite
    each_ring_line: SpriteGroup
    
    normal_note: Sprite
    break_note_light: Sprite
    break_note_dark: Sprite
    each_note: Sprite

    normal_note_ex_outline: Sprite
    break_note_ex_outline: Sprite
    each_note_ex_outline: Sprite

    normal_star: Sprite
    break_star: Sprite
    each_star: Sprite

    double_star: Sprite
    break_double_star: Sprite
    each_double_star: Sprite

    normal_star_ex_outline: Sprite
    break_star_ex_outline: Sprite
    each_star_ex_outline: Sprite

    double_star_ex_outline: Sprite
    break_double_star_ex_outline: Sprite
    each_double_star_ex_outline: Sprite

    normal_touch_point: Sprite
    break_touch_point: Sprite
    each_touch_point: Sprite

    normal_touch_fan: Sprite
    break_touch_fan: Sprite
    each_touch_fan: Sprite

    normal_touch_overlap_border: SpriteGroup
    break_touch_overlap_border: SpriteGroup
    each_touch_overlap_border: SpriteGroup
    touch_just_border: Sprite

    slide_path: Sprite
    break_slide_path: Sprite
    each_slide_path: Sprite

    wifi_slide_paths: SpriteGroup
    break_wifi_slide_paths: SpriteGroup
    each_wifi_slide_paths: SpriteGroup

    ring: Sprite
    sensor_outline: Sprite


def init_skin():
    ActiveSkin.white_square @= BaseSkin.white_square
    ActiveSkin.white_outline @= BaseSkin.white_outline

    ActiveSkin.normal_line @= BaseSkin.normal_line
    ActiveSkin.break_line @= BaseSkin.break_line
    ActiveSkin.each_line @= BaseSkin.each_line
    ActiveSkin.star_line @= BaseSkin.star_line
    ActiveSkin.each_ring_line @= BaseSkin.each_ring_line
    
    ActiveSkin.normal_note @= BaseSkin.normal_note
    ActiveSkin.break_note_dark @= BaseSkin.break_note_dark
    ActiveSkin.break_note_light @= BaseSkin.break_note_light
    ActiveSkin.each_note @= BaseSkin.each_note

    ActiveSkin.normal_star = BaseSkin.normal_star
    ActiveSkin.break_star @= BaseSkin.break_star
    ActiveSkin.each_star @= BaseSkin.each_star
    ActiveSkin.double_star @= BaseSkin.double_star
    ActiveSkin.break_double_star @= BaseSkin.break_double_star
    ActiveSkin.each_double_star @= BaseSkin.each_double_star

    ActiveSkin.normal_note_ex_outline @= BaseSkin.normal_note_ex_outline
    ActiveSkin.break_note_ex_outline @= BaseSkin.break_note_ex_outline
    ActiveSkin.each_note_ex_outline @= BaseSkin.each_note_ex_outline
    ActiveSkin.normal_star_ex_outline @= BaseSkin.normal_star_ex_outline
    ActiveSkin.break_star_ex_outline @= BaseSkin.break_star_ex_outline
    ActiveSkin.each_star_ex_outline @= BaseSkin.each_star_ex_outline
    ActiveSkin.double_star_ex_outline @= BaseSkin.double_star_ex_outline
    ActiveSkin.break_double_star_ex_outline @= BaseSkin.break_double_star_ex_outline
    ActiveSkin.each_double_star_ex_outline @= BaseSkin.each_double_star_ex_outline

    ActiveSkin.normal_touch_point @= BaseSkin.normal_touch_point
    ActiveSkin.break_touch_point @= BaseSkin.break_touch_point
    ActiveSkin.each_touch_point @= BaseSkin.each_touch_point

    ActiveSkin.normal_touch_fan @= BaseSkin.normal_touch_fan
    ActiveSkin.break_touch_fan @= BaseSkin.break_touch_fan
    ActiveSkin.each_touch_fan @= BaseSkin.each_touch_fan

    ActiveSkin.normal_touch_overlap_border @= BaseSkin.normal_touch_overlap_border
    ActiveSkin.break_touch_overlap_border @= BaseSkin.break_touch_overlap_border
    ActiveSkin.each_touch_overlap_border @= BaseSkin.each_touch_overlap_border
    ActiveSkin.touch_just_border @= BaseSkin.touch_just_border

    ActiveSkin.slide_path @= BaseSkin.slide_path
    ActiveSkin.break_slide_path @= BaseSkin.break_slide_path
    ActiveSkin.each_slide_path @= BaseSkin.each_slide_path

    ActiveSkin.wifi_slide_paths @= BaseSkin.wifi_slide_paths
    ActiveSkin.break_wifi_slide_paths @= BaseSkin.break_wifi_slide_paths
    ActiveSkin.each_wifi_slide_paths @= BaseSkin.each_wifi_slide_paths

    
    ActiveSkin.ring @= BaseSkin.ring
    ActiveSkin.sensor_outline @= BaseSkin.sensor_outline

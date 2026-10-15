import cv2


def draw_overlay(frame, stats, room_state):
    """Render a high-visibility HUD on *frame* in-place and return it.

    Every label is drawn twice: first with a thick black stroke (outline),
    then with the colour on top, so the text is legible against any background.
    """
    h, w = frame.shape[:2]

    # Palette — chosen to stand out on both dark and light backgrounds
    OUTLINE   = (0,   0,   0)     # black stroke
    PEOPLE_C  = (255, 255,  50)   # yellow
    LIGHT_C   = ( 50, 255, 120)   # lime-green
    STATUS_OK = ( 50, 230,  80)   # green
    STATUS_BAD= (255,  80,  80)   # red
    COST_C    = (255, 200,  50)   # amber
    BRIGHT_C  = (200, 200, 255)   # lavender

    STATUS_C  = STATUS_BAD if room_state["status"] in ["WASTE", "INEFFICIENT"] else STATUS_OK

    font      = cv2.FONT_HERSHEY_SIMPLEX
    fg_thick  = 2
    out_thick = 4

    def _put(img, text, pos, scale, color):
        cv2.putText(img, text, pos, font, scale, OUTLINE,  out_thick, cv2.LINE_AA)
        cv2.putText(img, text, pos, font, scale, color,    fg_thick,  cv2.LINE_AA)

    # Top-left block
    _put(frame, f"People  : {stats['person_count']}",                    (18,  42), 0.85, PEOPLE_C)
    _put(frame, f"Light   : {'ON' if stats['lights_on'] else 'OFF'}",    (18,  80), 0.85, LIGHT_C)
    _put(frame, f"Status  : {room_state['status']}",                      (18, 118), 0.85, STATUS_C)
    _put(frame, f"Waste   : Rs {room_state['cost_inr_wasted']:.4f}",     (18, 154), 0.80, COST_C)

    # Bottom-right: brightness
    br_text = f"Brightness: {stats.get('brightness', 0):.1f}"
    (tw, _), _ = cv2.getTextSize(br_text, font, 0.65, fg_thick)
    _put(frame, br_text, (w - tw - 16, h - 16), 0.65, BRIGHT_C)

    return frame

"""
Hero grid navigation for Valkyrie Connect.

Relies entirely on auto_farmeo_valkyrie.py (imports it, no code duplication).
Uses perceptual hashing of hero name regions (not OCR) to avoid reprocessing
heroes after scrolling. Completion is checked via template matching of the
"9/9" badge rather than reading text.

Requires in templates/:
    insignia_completa.png   -> exact crop of the gold star + "9/9" badge
                               displayed when a hero is 100% complete.

Usage:
    python recorrido_heroes.py
"""

from __future__ import annotations

import random
import time
from typing import Optional

import pyscreeze

import pyautogui

import auto_farmeo_valkyrie
from auto_farmeo_valkyrie import (
    TEMPLATES_DIR,
    find_any,
    find_all_on_screen,
    CONFIDENCE_BADGE,
    wait_ms,
    clear_hero_path,
    claim_chests,
    return_to_hero_list,
)


def _click_point(point: tuple) -> None:
    x, y = point
    pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))
    pyautogui.click()
    wait_ms()


GRID_COLS_X = [0.339, 0.677]
GRID_ROWS_Y = [0.386, 0.564, 0.741]

NAME_OFFSET = (-126, -60, 400, 36)


def _to_absolute(rel_x: float, rel_y: float) -> tuple:
    w, h = pyautogui.size()
    return int(w * rel_x), int(h * rel_y)


def scroll_drag(distance_px: int = 500, duration: float = 0.6) -> None:
    w, h = pyautogui.size()
    x = w // 2
    y_start = int(h * 0.75)
    y_end = max(int(h * 0.75) - distance_px, int(h * 0.15))
    pyautogui.moveTo(x, y_start, duration=0.2)
    pyautogui.mouseDown()
    pyautogui.moveTo(x, y_end, duration=duration)
    time.sleep(0.1)
    pyautogui.mouseUp()
    wait_ms(0.8, 1.2)


def _find_actual_row(col_x: float, approx_row_y: float, search_range: int = 140, step: int = 8, threshold: int = 12) -> Optional[tuple]:
    cx, cy_approx = _to_absolute(col_x, approx_row_y)
    ox, oy, ow, oh = NAME_OFFSET
    name_y_base = cy_approx + oy
    offsets = [0]
    for d in range(step, search_range + 1, step):
        offsets.append(d)
        offsets.append(-d)
    for delta in offsets:
        cy_test = name_y_base + delta
        region = (cx + ox, cy_test, ow, oh)
        if _is_name_readable(region, threshold):
            return cx, cy_test, region
    return None


def detect_grid_cards() -> list:
    cards = []
    for row_y in GRID_ROWS_Y:
        for col_x in GRID_COLS_X:
            result = _find_actual_row(col_x, row_y)
            if result is None:
                continue
            cx, cy_real, name_region = result
            nx, ny, nw, nh = name_region
            card_center = (nx + nw // 2, ny + nh // 2)
            cards.append((card_center, name_region))
    return cards


def hash_region(region: tuple) -> Optional[str]:
    x, y, w, h = region
    try:
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
    except Exception:
        return None
    small = screenshot.convert("L").resize((8, 8))
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    return bits


def _hashes_are_similar(hash_a: Optional[str], hash_b: Optional[str], max_distance: int = 6) -> bool:
    if hash_a is None or hash_b is None or len(hash_a) != len(hash_b):
        return False
    distance = sum(a != b for a, b in zip(hash_a, hash_b))
    return distance <= max_distance


def _is_name_readable(region: tuple, threshold: int = 12) -> bool:
    x, y, w, h = region
    try:
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
    except Exception:
        return False
    pixels = list(screenshot.convert("L").getdata())
    mean = sum(pixels) / len(pixels)
    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    stddev = variance ** 0.5
    return stddev >= threshold


def _is_hero_complete(confidence: float = 0.96, timeout: int = 2) -> bool:
    template_path = TEMPLATES_DIR + "insignia_completa.png"
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            loc = pyautogui.locateOnScreen(template_path, confidence=confidence)
        except (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException):
            loc = None
        if loc:
            return True
        time.sleep(0.2)
    return False


def _is_on_hero_path_screen(timeout: int = 3) -> bool:
    return find_any(["flecha_volver.png", "icono_disponible.png"], timeout=timeout, confidence=0.65) is not None


def _has_pending_nodes(timeout: int = 2, confidence: float = 0.75) -> bool:
    w, h = pyautogui.size()
    region = (int(w * 0.12), 0, int(w * 0.88), int(h * 0.82))

    first = find_all_on_screen("icono_disponible.png", confidence=confidence, timeout=timeout, region=region)
    if not first:
        return False
    time.sleep(0.4)
    second = find_all_on_screen("icono_disponible.png", confidence=confidence, timeout=timeout, region=region)
    return len(second) > 0


def process_all_heroes(max_scrolls_without_change: int = 3, scroll_distance: int = 550, stop_event=None) -> None:
    from auto_farmeo_valkyrie import stats
    stats['heroes_completados'] = 0
    stats['libros_completados'] = 0
    stats['cofre1_abiertos'] = 0
    stats['cofre2_abiertos'] = 0
    stats['cofre3_abiertos'] = 0
    last_row_hashes = []
    newly_completed = 0
    scrolls_without_change = 0

    def _should_stop():
        return (stop_event and stop_event.is_set()) or auto_farmeo_valkyrie.stop_event.is_set()

    while True:
        if _should_stop():
            print('Farming stopped by user.')
            break

        cards = detect_grid_cards()

        adjust_attempts = 0
        while len(cards) < 6 and adjust_attempts < 3 and not _should_stop():
            print(f"  [WARN] Only {len(cards)}/6 cards detected. "
                  f"Adjusting with small scroll ({adjust_attempts + 1}/3)...")
            scroll_drag(distance_px=110)
            cards = detect_grid_cards()
            adjust_attempts += 1

        if _should_stop():
            print('Farming stopped by user.')
            break

        if len(cards) < 4:
            scrolls_without_change += 1
            if scrolls_without_change >= max_scrolls_without_change:
                print("No new heroes after multiple scrolls. Ending.")
                break
            scroll_drag(distance_px=scroll_distance)
            continue

        start_index = 0
        if last_row_hashes and _is_name_readable(cards[0][1]):
            hash_first_card = hash_region(cards[0][1])
            if any(_hashes_are_similar(hash_first_card, h) for h in last_row_hashes):
                print("  Top row was already processed before scroll. Skipping...")
                start_index = min(2, len(cards))

        found_new = False
        for card_click, name_region in cards[start_index:]:
            if _should_stop():
                print('Farming stopped by user.')
                return
            current_hash = hash_region(name_region)
            if current_hash and any(_hashes_are_similar(current_hash, h) for h in last_row_hashes):
                print("  Duplicate hero. Skipping...")
                continue
            _click_point(card_click)
            wait_ms(0.8, 1.3)
            if not _is_on_hero_path_screen():
                print("  [WARN] Click did not open a valid hero path. Skipping.")
                continue
            if _is_hero_complete() and not _has_pending_nodes():
                print("  Hero complete (9/9) with no pending nodes. Skipping...")
            elif not _has_pending_nodes():
                print("  Hero has no pending nodes (badge not showing 9/9). Skipping...")
            else:
                print("  Hero has pending nodes (books and/or battles). Resolving...")
                clear_hero_path()
                if _should_stop():
                    print('Farming stopped by user (during path).')
                    return
                claim_chests()
                newly_completed += 1
                stats['heroes_completados'] = newly_completed

            found_new = True
            return_to_hero_list()
            wait_ms(0.8, 1.2)

        tail = cards[-2:] if len(cards) >= 2 else cards[-1:]
        last_row_hashes = [hash_region(t[1]) for t in tail]

        if found_new:
            scrolls_without_change = 0
        else:
            scrolls_without_change += 1
            if scrolls_without_change >= max_scrolls_without_change:
                print("No new heroes after multiple scrolls. Ending.")
                break

        scroll_drag(distance_px=scroll_distance)

    print(f"=== Run finished. Heroes with new rewards: {newly_completed} ===")


def main() -> None:
    print("=== Starting auto-farming across ALL heroes ===")
    print("Make sure the hero selection menu is open.")
    print("You have 5 seconds to focus the game window...")
    time.sleep(5)
    process_all_heroes()


if __name__ == "__main__":
    main()

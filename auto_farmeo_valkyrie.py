"""
Hero mission automation for Valkyrie Connect.

Uses screen image recognition (template matching via pyautogui/OpenCV) to
automatically navigate hero missions, resolve story nodes and battles, and
claim rewards. No memory reading or game hacking involved.

Expected folder structure:
    templates/
        icono_disponible.png       -> orange circle with "!" (pending node)
        icono_libro.png            -> book icon (fallback)
        boton_omitir.png           -> "Skip" button for story scenes
        boton_aceptar_omitir.png   -> confirmation after pressing Skip
        boton_play.png             -> Play button (ready/select/next)
        pantalla_resultados.png    -> victory screen (wings + 3 gold stars)
        cofre_1.png                -> first chest (wood)
        cofre_2.png                -> second chest (silver/orange)
        cofre_3.png                -> third chest (gold with gem)
        flecha_volver.png          -> back arrow to return to hero list
        icono_heroe_disponible.png -> marker for hero with available missions

The 'templates' folder must be in the same directory as this script
(the path is resolved automatically at runtime).
"""

from __future__ import annotations

import os
import random
import threading
import time
from typing import Optional

import pyscreeze

import pyautogui

VERSION = "1.0.0"

pyautogui.FAILSAFE = True  # move mouse to top-left corner to abort

# Shared stop event. Set by the GUI (or another script) to interrupt any
# long-running operation (nodes, battles, chests) immediately.
stop_event = threading.Event()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates") + os.sep

CONFIDENCE = 0.8
CONFIDENCE_BADGE = 0.65  # "!" badge sometimes scores low (0.6-0.85)

# Stats tracking (read by GUI thread)
stats = {
    "heroes_completados": 0,
    "libros_completados": 0,
    "cofre1_abiertos": 0,
    "cofre2_abiertos": 0,
    "cofre3_abiertos": 0,
}


# ---------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------
def wait_ms(a: float = 0.5, b: float = 1.5) -> None:
    time.sleep(random.uniform(a, b))


def find_on_screen(template_name: str, confidence: float = CONFIDENCE, timeout: int = 5) -> Optional[pyautogui.Point]:
    template_path = TEMPLATES_DIR + template_name
    end_time = time.time() + timeout
    while time.time() < end_time:
        if stop_event.is_set():
            return None
        try:
            loc = pyautogui.locateCenterOnScreen(template_path, confidence=confidence)
            if loc:
                return loc
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    return None


def find_all_on_screen(
    template_name: str,
    confidence: float = CONFIDENCE,
    min_dist: int = 25,
    timeout: int = 3,
    region: Optional[tuple] = None,
) -> list:
    template_path = TEMPLATES_DIR + template_name
    end_time = time.time() + timeout
    while time.time() < end_time:
        if stop_event.is_set():
            return []
        results = []
        try:
            if region:
                boxes = list(pyautogui.locateAllOnScreen(template_path, confidence=confidence, region=region))
            else:
                boxes = list(pyautogui.locateAllOnScreen(template_path, confidence=confidence))
        except (pyautogui.ImageNotFoundException, pyscreeze.ImageNotFoundException):
            boxes = []

        for box in boxes:
            center = pyautogui.center(box)
            if all(abs(center.x - c.x) > min_dist or abs(center.y - c.y) > min_dist for c in results):
                results.append(center)

        if results:
            return results
        time.sleep(0.3)
    return []


def click_point(point: pyautogui.Point) -> None:
    pyautogui.moveTo(point.x, point.y, duration=random.uniform(0.1, 0.3))
    pyautogui.click()
    wait_ms()


def click_center_screen() -> None:
    w, h = pyautogui.size()
    pyautogui.click(w // 2, int(h * 0.45))  # away from taskbar
    wait_ms()


def click_image(template_name: str, confidence: float = CONFIDENCE, timeout: int = 5) -> bool:
    loc = find_on_screen(template_name, confidence, timeout)
    if loc:
        click_point(loc)
        return True
    print(f"  [SKIP] {template_name} not found.")
    return False


def find_any(templates: list, timeout: int = 3, confidence: float = CONFIDENCE) -> Optional[pyautogui.Point]:
    for tmpl in templates:
        res = find_on_screen(tmpl, timeout=timeout, confidence=confidence)
        if res:
            return res
    return None


def click_any(templates: list, timeout: int = 3, confidence: float = CONFIDENCE) -> bool:
    for tmpl in templates:
        res = find_on_screen(tmpl, timeout=timeout, confidence=confidence)
        if res:
            click_point(res)
            return True
    print(f"  [SKIP] None of {templates} found.")
    return False


# ---------------------------------------------------------
# FASE 2.1 - Nodo de LIBRO (historia)
# ---------------------------------------------------------
def _resolve_book_scene() -> None:
    stats["libros_completados"] += 1
    print("  -> Book node detected. Skipping story...")
    loc = find_on_screen("boton_aceptar_omitir.png", confidence=0.7, timeout=4)
    if loc:
        click_point(loc)
    else:
        print("  [SKIP] boton_aceptar_omitir.png not found.")
    time.sleep(1.5)
    click_center_screen()
    time.sleep(1.0)
    click_center_screen()


# ---------------------------------------------------------
# PHASE 2.2 - Battle node
# ---------------------------------------------------------
def _resolve_battle() -> None:
    print("  -> Battle node detected. Fighting...")
    click_image("boton_play_v2.png", confidence=0.7, timeout=8)

    print("     Waiting for battle result...")
    result = find_on_screen("pantalla_resultados.png", confidence=0.65, timeout=45)
    if stop_event.is_set():
        return
    if not result:
        print("     [SKIP] Result screen not detected, waiting extra...")
        time.sleep(8)

    print("     Dismissing reward screen...")
    click_center_screen()
    time.sleep(1.0)
    click_center_screen()
    time.sleep(1.0)

    print("     Waiting for return-to-map button...")
    button = find_any(["boton_Play_Final_Stage.png", "boton_play_v2.png", "boton_play.png"],
                      timeout=15, confidence=0.7)
    if button:
        click_point(button)
        time.sleep(0.3)
        click_point(button)


def _resolve_pending_node(badge_point: pyautogui.Point) -> None:
    click_point(badge_point)

    skip = find_on_screen("boton_omitir.png", confidence=0.7, timeout=0.8)
    if skip:
        click_point(skip)
        _resolve_book_scene()
        return

    play = find_any(["boton_play.png", "boton_play_v2.png"], timeout=3, confidence=0.6)
    if play:
        click_point(play)
        _resolve_battle()
        return

    print("  [WARN] Could not identify node type after click. Retrying...")
    click_point(badge_point)
    skip = find_on_screen("boton_omitir.png", confidence=0.7, timeout=0.8)
    if skip:
        click_point(skip)
        _resolve_book_scene()
        return
    play = find_any(["boton_play.png", "boton_play_v2.png"], timeout=3, confidence=0.6)
    if play:
        click_point(play)
        _resolve_battle()
        return
    print("  [ERROR] Node unresolved after retry. Skipping.")


# ---------------------------------------------------------
# PHASE 2 (loop) - Clear all pending nodes on the hero path
# ---------------------------------------------------------
def clear_hero_path() -> None:
    empty_attempts = 0
    max_empty_attempts = 3
    max_nodes = 6
    nodes_done = 0

    w, h = pyautogui.size()
    search_region = (int(w * 0.12), 0, int(w * 0.88), int(h * 0.82))

    while nodes_done < max_nodes:
        if stop_event.is_set():
            print("  Farming stopped by user (inside hero path).")
            break
        badges = find_all_on_screen("icono_disponible.png", confidence=CONFIDENCE_BADGE,
                                     timeout=3, region=search_region)

        if badges:
            print(f"  Pending nodes: {len(badges)}. "
                  f"Resolving ({nodes_done + 1}/{max_nodes})...")
            _resolve_pending_node(badges[0])
            nodes_done += 1
            empty_attempts = 0
            time.sleep(1)
        else:
            empty_attempts += 1
            print(f"  No pending nodes found. "
                  f"Attempt {empty_attempts}/{max_empty_attempts}.")
            if empty_attempts >= max_empty_attempts:
                break
            click_center_screen()
            time.sleep(1)

    print(f"  Hero path cleared ({nodes_done}/{max_nodes} nodes resolved).")


# ---------------------------------------------------------
# PHASE 3 - Claim the 3 final chests
# ---------------------------------------------------------
def claim_chests() -> None:
    print("Claiming final chests...")
    for name in ["cofre_1.png", "cofre_2.png", "cofre_3.png"]:
        if stop_event.is_set():
            print("  Farming stopped by user (inside chests).")
            break
        chest = find_on_screen(name, timeout=8)
        if chest:
            click_point(chest)
            if name == "cofre_1.png":
                stats["cofre1_abiertos"] += 1
            elif name == "cofre_2.png":
                stats["cofre2_abiertos"] += 1
            elif name == "cofre_3.png":
                stats["cofre3_abiertos"] += 1
            time.sleep(2.5)
            w, h = pyautogui.size()
            pyautogui.click(w // 2 + 220, int(h * 0.45))
            time.sleep(2.5)
        else:
            print(f"  [SKIP] {name} not found.")


# ---------------------------------------------------------
# Utility: navigate back to hero list
# ---------------------------------------------------------
def return_to_hero_list() -> None:
    click_image("flecha_volver.png", timeout=5)


def _select_next_hero() -> bool:
    hero = find_on_screen("icono_heroe_disponible.png", timeout=3)
    if hero:
        click_point(hero)
        return True
    else:
        print("No heroes with pending missions visible. Scrolling...")
        w, h = pyautogui.size()
        pyautogui.moveTo(w // 2, h // 2)
        pyautogui.scroll(-300)
        time.sleep(1)
        return False


def run_single_mission() -> None:
    print("=== Test mode: resolving ONE mission ===")
    print("Make sure the hero path screen (books/battles) is already open.")
    print("You have 5 seconds to focus the game window...")
    time.sleep(5)

    clear_hero_path()
    claim_chests()
    return_to_hero_list()
    print("=== Test mission completed ===")


def run_all() -> None:
    print("=== Starting auto-farming of Hero Missions ===")
    print("You have 5 seconds to focus the game window...")
    time.sleep(5)

    processed_heroes = 0
    empty_scrolls = 0

    while True:
        entered = _select_next_hero()
        if not entered:
            empty_scrolls += 1
            if empty_scrolls >= 10:
                print("No more heroes available. Finishing.")
                break
            continue

        empty_scrolls = 0
        clear_hero_path()
        claim_chests()
        return_to_hero_list()
        processed_heroes += 1
        print(f"### Hero #{processed_heroes} completed. ###\n")
        time.sleep(1.5)

    print(f"=== Script finished. Total heroes processed: {processed_heroes} ===")


if __name__ == "__main__":
    run_single_mission()

import random
from typing import List, Dict, Any, Optional

from app.models.word import Word
from app.utils.constants import (
    OPTIONS_COUNT,
    POOL_EXERCISE_TYPES,
    EXERCISE_TYPE_ORDER,
    ExerciseType,
)


def generate_options(
    correct_word: Word,
    all_words: List[Word],
    session_words: Optional[List[Word]] = None,
) -> tuple[List[Dict[str, Any]], int]:
    """
    Generate randomized options for a question.

    Args:
        correct_word: The correct answer word
        all_words: All available words to pick distractors from
        session_words: Words in current session (prioritized for distractors)

    Returns:
        tuple: (options list, correct_index)
    """
    # Get distractor candidates
    # Priority: session words > all learned words
    distractor_candidates = []

    if session_words:
        distractor_candidates = [w for w in session_words if w.id != correct_word.id]

    # If not enough distractors from session, add from all words
    if len(distractor_candidates) < OPTIONS_COUNT - 1:
        additional = [
            w for w in all_words
            if w.id != correct_word.id and w not in distractor_candidates
        ]
        distractor_candidates.extend(additional)

    # Randomly select distractors
    num_distractors = min(OPTIONS_COUNT - 1, len(distractor_candidates))
    distractors = random.sample(distractor_candidates, num_distractors)

    # Create options list with correct answer
    options_words = distractors + [correct_word]

    # Shuffle to randomize correct answer position
    random.shuffle(options_words)

    # Find correct index
    correct_index = next(
        i for i, w in enumerate(options_words) if w.id == correct_word.id
    )

    # Build options data
    options = []
    for i, word in enumerate(options_words):
        options.append({
            "index": i,
            "word_id": str(word.id),
            "translation": word.translation,
            "image_url": word.image_url,
        })

    return options, correct_index


def build_exercise(
    word: Word,
    pool: str,
    all_words: List[Word],
    session_words: Optional[List[Word]] = None,
) -> Dict[str, Any]:
    """
    Build an exercise for a word based on its pool.

    Args:
        word: The word to create exercise for
        pool: The current pool of the word
        all_words: All available words for generating options
        session_words: Words in current session

    Returns:
        Exercise dictionary
    """
    exercise_type = POOL_EXERCISE_TYPES.get(pool)

    if not exercise_type:
        raise ValueError(f"No exercise type defined for pool {pool}")

    # Speaking exercises don't have options
    if exercise_type in [ExerciseType.SPEAKING_LV1, ExerciseType.SPEAKING_LV2]:
        return {
            "word_id": str(word.id),
            "word": word.word,
            "translation": word.translation,
            "image_url": word.image_url,
            "audio_url": word.audio_url,
            "pool": pool,
            "type": exercise_type.value,
            "options": [],
            "correct_index": None,
        }

    # Generate options for reading/listening exercises
    options, correct_index = generate_options(word, all_words, session_words)

    return {
        "word_id": str(word.id),
        "word": word.word,
        "translation": word.translation,
        "image_url": word.image_url,
        "audio_url": word.audio_url,
        "pool": pool,
        "type": exercise_type.value,
        "options": options,
        "correct_index": correct_index,
    }


def sort_exercises_by_type(exercises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort exercises by exercise type order (Reading -> Listening -> Speaking).
    """
    type_order = {t.value: i for i, t in enumerate(EXERCISE_TYPE_ORDER)}

    return sorted(
        exercises,
        key=lambda e: type_order.get(e["type"], 999)
    )


def get_exercise_order(exercises: List[Dict[str, Any]]) -> List[str]:
    """
    Get the unique exercise types in order from a list of exercises.
    """
    seen = set()
    order = []
    for ex in exercises:
        ex_type = ex["type"]
        if ex_type not in seen:
            seen.add(ex_type)
            order.append(ex_type)
    return order


def build_learn_exercise(
    word: Word,
    all_words: List[Word],
    session_words: Optional[List[Word]] = None,
) -> Dict[str, Any]:
    """
    Build a learning exercise (always Reading Lv1).
    """
    options, correct_index = generate_options(word, all_words, session_words)

    return {
        "word_id": str(word.id),
        "type": ExerciseType.READING_LV1.value,
        "options": options,
        "correct_index": correct_index,
    }


def build_word_detail(word: Word, pool: Optional[str] = None) -> Dict[str, Any]:
    """
    Build word detail for session response.
    """
    result = {
        "id": str(word.id),
        "word": word.word,
        "translation": word.translation,
        "sentence": word.sentence,
        "sentence_zh": word.sentence_zh,
        "image_url": word.image_url,
        "audio_url": word.audio_url,
    }

    if pool:
        result["pool"] = pool

    return result

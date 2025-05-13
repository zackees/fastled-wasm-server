import random
import string


def make_random_path_string(digits: int) -> str:
    """Generate a random number."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=digits))

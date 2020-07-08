import re

NB_VERSION = 4
BLOCK_QUOTE = "```"
COMMENT_PREFIX = "#"
TEST_HEADERS = ["TEST", "HIDDEN TEST"]
ALLOWED_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]*')
NB_VERSION = 4

TEST_REGEX = re.compile(r"(##\s*(hidden\s*)?test\s*##|#\s*(hidden\s*)?test)")
SOLUTION_REGEX = re.compile(r"##\s*solution\s*##")
MD_SOLUTION_REGEX = re.compile(r"(<strong>|\*{2})solution:?(<\/strong>|\*{2})")
SEED_REGEX = re.compile(r"##\s*seed\s*##")

MD_ANSWER_CELL_TEMPLATE = "_Type your answer here, replacing this text._"
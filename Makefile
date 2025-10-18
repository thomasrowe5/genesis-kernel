.PHONY: demo docs benchmark install

install:
	poetry install --no-interaction --no-ansi

benchmark:
	poetry run genesis benchmark run

docs:
	poetry run genesis docs build

demo:
	poetry run genesis deploy local

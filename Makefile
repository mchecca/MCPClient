.PHONY: forms

all: forms

forms:
	make -C forms

clean:
	rm -rf ui_* *.pyc __pycache__

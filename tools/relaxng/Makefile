.PHONY: all clean

all: yin-html.rnc

%.rnc: %.rng
	trang -I rng -O rnc $< $@

clean:
	rm -f *.rnc

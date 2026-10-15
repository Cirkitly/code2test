# Build the paper and the arXiv submission bundle.
#   make          -> main.pdf
#   make arxiv    -> arxiv.tar.gz (sources + main.bbl; arXiv does not run BibTeX)
#   make clean

SOURCES = main.tex results.tex references.bib figures/pipeline.tex

main.pdf: $(SOURCES)
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

arxiv: main.pdf
	rm -rf arxiv arxiv.tar.gz
	mkdir -p arxiv/figures
	cp main.tex results.tex main.bbl arxiv/
	cp figures/pipeline.tex arxiv/figures/
	tar -czf arxiv.tar.gz -C arxiv .
	@echo "Upload arxiv.tar.gz at https://arxiv.org/submit (category cs.SE)."

clean:
	latexmk -C main.tex
	rm -rf arxiv arxiv.tar.gz main.bbl

.PHONY: arxiv clean

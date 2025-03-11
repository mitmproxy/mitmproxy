{{/*
    This file contains the search index and is only loaded on demand (when the user focuses the search field).
*/}}

window.docsSearch = (function(){
    {{ (resources.Get "elasticlunr.min.js").Content | safeJS }}

    /** search index */
    {{- $pages := slice -}}
    {{- range .Site.RegularPages -}}
        {{- $sectionTitle := "" -}}
        {{- with .Site.GetPage (printf "/%s" .Section) -}}
            {{- $sectionTitle = .Title -}}
        {{- end -}}
        {{- $page := dict 
            "title" .Title
            "url" .RelPermalink
            "content" .Plain
            "section" $sectionTitle
        -}}
        {{- $pages = $pages | append $page -}}
    {{- end -}}
    const docs = {{ $pages | jsonify }};

    // Also split on html tags. this is a cheap heuristic, but good enough.
    elasticlunr.tokenizer.setSeperator(/[\s\-.;&_'"=,()]+|<[^>]*>/);

    console.time("building search index");
    // mirrored in build-search-index.js (part 2)
    let searchIndex = elasticlunr(function () {
        this.pipeline.remove(elasticlunr.stemmer);
        this.pipeline.remove(elasticlunr.stopWordFilter);
        this.addField("title");
        this.addField("content");
        this.addField("section");
        this.setRef("url");
    });
    for (let doc of docs) {
        searchIndex.addDoc(doc);
    }
    console.timeEnd("building search index");

    return (term) => searchIndex.search(term, {
        fields: {
            title: {boost: 4},
            content: {boost: 1},
            section: {boost: 2}
        },
        expand: true
    });
})(); 
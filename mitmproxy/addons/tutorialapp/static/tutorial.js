var ajaxButtons = document.getElementsByClassName('ajax-btn');

for(let i = 0; i < ajaxButtons.length; i++) {
    ajaxButtons[i].addEventListener("click", function(e) {
        fetch(e.currentTarget.href)
            .then(response => response.json())
            .then(data => {
                document.getElementById("votes-cat").innerHTML = data["cat"];
                document.getElementById("votes-dog").innerHTML = data["dog"];
            });

        e.preventDefault();
        return false;
    })
}

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("btn-reload-votes").click();
    $('[data-toggle="tooltip"]').tooltip();
});

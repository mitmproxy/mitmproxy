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


var timer;

function playEvent(e) {
    console.log("playing at " + this.currentTime);
    var playStartPosition = this.currentTime;
    var playStartDate = new Date();
    var annotations = this.annotations;

    timer = setInterval(function(){
        var now = new Date();
        updateAnnotations(playStartPosition + (now - playStartDate) / 1000, annotations);
    }, 250);
}

function pauseEvent(e) {
    console.log("paused");
    if (timer){
        clearInterval(timer);
    }
}

function updateAnnotations(playedTimeSecs, annotations){
    for(let i = 0; i < annotations.length; i++) {
        if (annotations[i].getAttribute("data-from") < playedTimeSecs && annotations[i].getAttribute("data-to") > playedTimeSecs) {
            annotations[i].style.display = "block";
        }
        else {
            annotations[i].style.display = "none";
        }
    }
}


document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("btn-reload-votes").click();
    $('[data-toggle="tooltip"]').tooltip();

    var asciiPlayers = document.getElementsByTagName('asciinema-player');

    for(let i = 0; i < asciiPlayers.length; i++) {
        asciiPlayers[i].annotations = asciiPlayers[i].parentElement.getElementsByClassName("annotation");
        asciiPlayers[i].addEventListener("play", playEvent);
        asciiPlayers[i].addEventListener('pause', pauseEvent);
    }
});

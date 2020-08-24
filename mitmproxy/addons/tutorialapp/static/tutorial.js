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
    var player = this;
    timer = setInterval(function(){
        updateInstructions(player);
    }, 250);
}

function pauseEvent(e) {
    console.log("paused");
    if (timer){
        clearInterval(timer);
    }
}

function updateInstructions(player) {
   var instructions = player.instructions;
   var currTime = player.currentTime;
    for(let i = 0; i < instructions.length; i++) {
        if (instructions[i].getAttribute("data-from") < currTime
            && instructions[i].getAttribute("data-to") > currTime) {
            instructions[i].classList.add("active");
        }
        else {
            instructions[i].classList.remove("active");
        }
    }
}


document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("btn-reload-votes").click();

    var asciinemaPlayer = document.getElementById('asciinema-player');
    asciinemaPlayer.instructions = asciinemaPlayer.parentElement.parentElement.getElementsByClassName("list-group-item-action");
    asciinemaPlayer.addEventListener("play", playEvent);
    asciinemaPlayer.addEventListener('pause', pauseEvent);

    for(let i = 0; i < asciinemaPlayer.instructions.length; i++) {
        var instruction = asciinemaPlayer.instructions[i];
        instruction.addEventListener("click", function(e){
            asciinemaPlayer.currentTime = this.getAttribute("data-from");
            asciinemaPlayer.play();
            e.preventDefault();
            return false;
        });
    }
});

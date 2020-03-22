var img1 = "static/PlayStation-DualShock-4.jpg"

window.onload = function () {
    var canvas = document.getElementById("c1")
    ctx = canvas.getContext('2d')
    width = canvas.width
    height = canvas.height

    windowWidth = document.body.offsetWidth
    windowHeight = document.body.offsetHeight

    document.addEventListener('mousemove', function(e){
        console.log('hi')
        log(`width: ${windowWidth}, height: ${windowHeight}, X: ${e.clientX}(${e.clientX/windowWidth}), Y: ${e.clientY}(${e.clientY/windowHeight})`)
    })


    ctx.imageSmoothingEnabled = false
    img1 = new Image()
    img1.src = "static/PlayStation-DualShock-4.jpg"
    img1.height = height
    img1.width = width

    img1.onload = function () {
        ctx.drawImage(img1, 0, 0, width, height)
    }
    console.log(ctx)
    log('nihao')

    let up = {
        center: [0.196, 0.235],
        radius: 0.035
    }
    let down = {

    }
    let left = {}
    let right = {}
    let cameraUp = {}
    let cameraDown = {}
    let liftUp = {}
    let liftDown = {}
}


function log(msg){
    document.getElementById('msg').innerText = msg;
}
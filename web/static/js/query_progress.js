$(function worker() {
    $.get("/task/update/all", function (data) {
        if (!$.isEmptyObject(data)) {
            $.each(data, function (id, status) {
                console.log(id, status)
                $("#status-" + id).text(status)
            });
            setTimeout(worker, 1000);
        }
    })
});


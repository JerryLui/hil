var ids = [];

function checker() {
    $.each(ids, function updater(index, value) {
        status_text = $('#status-' + value).text();
        if (status_text !== 'Finished' && status_text !== 'Failed') {
            return false;
        }
    });
    return true;
}

// Fill ids array
$('#tasks tr th').each(function () {
    ids.push(parseInt($(this).text()));
});


$(function status_worker() {
    if (checker()) {
        $('#status-sum').text('Finished');
    } else {
        $('#status-sum').text('In Progress');
        setTimeout(status_worker, 1000);
    }
});
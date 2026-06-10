import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: page

    property alias cfg_locationSearch: locationField.text
    property alias cfg_radarStation:   radarField.text
    property int   cfg_pollInterval:   plasmoid.configuration.pollInterval

    QQC2.TextField {
        id: locationField
        Kirigami.FormData.label: i18n("Location:")
        placeholderText: "Seaford VIC"
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
    }

    QQC2.TextField {
        id: radarField
        Kirigami.FormData.label: i18n("Radar station ID:")
        placeholderText: "IDR022"
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
    }

    QQC2.SpinBox {
        id: intervalSpin
        Kirigami.FormData.label: i18n("Update interval:")
        from: 5
        to: 60
        value: cfg_pollInterval / 60000
        onValueModified: cfg_pollInterval = value * 60000
        textFromValue: function(v) { return v + " min" }
        valueFromText: function(t) { return parseInt(t) || 10 }
    }

    Item { Kirigami.FormData.isSection: true }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        type: Kirigami.MessageType.Information
        visible: true
        text: i18n("Location: use 'Suburb STATE', e.g. 'Seaford VIC' or 'Sydney NSW'.\n" +
                   "Radar IDs: IDR022 = Melbourne 64 km · IDR023 = Melbourne 128 km · IDR003 = Sydney 64 km")
    }
}

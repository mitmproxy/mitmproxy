#!/usr/bin/env python3
'''
@author: David Shaw, shawd@vmware.com

Inspired by EAS Inspector for Fiddler
https://easinspectorforfiddler.codeplex.com

----- The MIT License (MIT) ----- 
Filename: ASWBXML.py
Copyright (c) 2014, David P. Shaw

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''
import xml.dom.minidom
import logging

from .ASWBXMLCodePage import ASWBXMLCodePage
from .ASWBXMLByteQueue import ASWBXMLByteQueue
from .GlobalTokens import GlobalTokens
from .InvalidDataException import InvalidDataException

class ASWBXML:
	versionByte = 0x03
	publicIdentifierByte = 0x01
	characterSetByte = 0x6A
	stringTableLengthByte = 0x00
	
	def __init__(self):
		
		# empty on init
		self.xmlDoc = xml.dom.minidom.Document()
		self.currentCodePage = 0
		self.defaultCodePage = -1
		
		# Load up code pages
		# Currently there are 25 code pages as per MS-ASWBXML
		self.codePages = []

		# region Code Page Initialization
		# Code Page 0: AirSync
		# region AirSync Code Page
		page = ASWBXMLCodePage()
		page.namespace = "AirSync:"
		page.xmlns = "airsync"

		page.addToken(0x05, "Sync")
		page.addToken(0x06, "Responses")
		page.addToken(0x07, "Add")
		page.addToken(0x08, "Change")
		page.addToken(0x09, "Delete")
		page.addToken(0x0A, "Fetch")
		page.addToken(0x0B, "SyncKey")
		page.addToken(0x0C, "ClientId")
		page.addToken(0x0D, "ServerId")
		page.addToken(0x0E, "Status")
		page.addToken(0x0F, "Collection")
		page.addToken(0x10, "Class")
		page.addToken(0x12, "CollectionId")
		page.addToken(0x13, "GetChanges")
		page.addToken(0x14, "MoreAvailable")
		page.addToken(0x15, "WindowSize")
		page.addToken(0x16, "Commands")
		page.addToken(0x17, "Options")
		page.addToken(0x18, "FilterType")
		page.addToken(0x1B, "Conflict")
		page.addToken(0x1C, "Collections")
		page.addToken(0x1D, "ApplicationData")
		page.addToken(0x1E, "DeletesAsMoves")
		page.addToken(0x20, "Supported")
		page.addToken(0x21, "SoftDelete")
		page.addToken(0x22, "MIMESupport")
		page.addToken(0x23, "MIMETruncation")
		page.addToken(0x24, "Wait")
		page.addToken(0x25, "Limit")
		page.addToken(0x26, "Partial")
		page.addToken(0x27, "ConversationMode")
		page.addToken(0x28, "MaxItems")
		page.addToken(0x29, "HeartbeatInterval")
		self.codePages.append(page)
		# endregion

		# Code Page 1: Contacts
		# region Contacts Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Contacts:"
		page.xmlns = "contacts"

		page.addToken(0x05, "Anniversary")
		page.addToken(0x06, "AssistantName")
		page.addToken(0x07, "AssistantTelephoneNumber")
		page.addToken(0x08, "Birthday")
		page.addToken(0x0C, "Business2PhoneNumber")
		page.addToken(0x0D, "BusinessCity")
		page.addToken(0x0E, "BusinessCountry")
		page.addToken(0x0F, "BusinessPostalCode")
		page.addToken(0x10, "BusinessState")
		page.addToken(0x11, "BusinessStreet")
		page.addToken(0x12, "BusinessFaxNumber")
		page.addToken(0x13, "BusinessPhoneNumber")
		page.addToken(0x14, "CarPhoneNumber")
		page.addToken(0x15, "Categories")
		page.addToken(0x16, "Category")
		page.addToken(0x17, "Children")
		page.addToken(0x18, "Child")
		page.addToken(0x19, "CompanyName")
		page.addToken(0x1A, "Department")
		page.addToken(0x1B, "Email1Address")
		page.addToken(0x1C, "Email2Address")
		page.addToken(0x1D, "Email3Address")
		page.addToken(0x1E, "FileAs")
		page.addToken(0x1F, "FirstName")
		page.addToken(0x20, "Home2PhoneNumber")
		page.addToken(0x21, "HomeCity")
		page.addToken(0x22, "HomeCountry")
		page.addToken(0x23, "HomePostalCode")
		page.addToken(0x24, "HomeState")
		page.addToken(0x25, "HomeStreet")
		page.addToken(0x26, "HomeFaxNumber")
		page.addToken(0x27, "HomePhoneNumber")
		page.addToken(0x28, "JobTitle")
		page.addToken(0x29, "LastName")
		page.addToken(0x2A, "MiddleName")
		page.addToken(0x2B, "MobilePhoneNumber")
		page.addToken(0x2C, "OfficeLocation")
		page.addToken(0x2D, "OtherCity")
		page.addToken(0x2E, "OtherCountry")
		page.addToken(0x2F, "OtherPostalCode")
		page.addToken(0x30, "OtherState")
		page.addToken(0x31, "OtherStreet")
		page.addToken(0x32, "PagerNumber")
		page.addToken(0x33, "RadioPhoneNumber")
		page.addToken(0x34, "Spouse")
		page.addToken(0x35, "Suffix")
		page.addToken(0x36, "Title")
		page.addToken(0x37, "Webpage")
		page.addToken(0x38, "YomiCompanyName")
		page.addToken(0x39, "YomiFirstName")
		page.addToken(0x3A, "YomiLastName")
		page.addToken(0x3C, "Picture")
		page.addToken(0x3D, "Alias")
		page.addToken(0x3E, "WeightedRank")
		self.codePages.append(page)
		# endregion

		# Code Page 2: Email
		# region Email Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Email:"
		page.xmlns = "email"

		page.addToken(0x0F, "DateReceived")
		page.addToken(0x11, "DisplayTo")
		page.addToken(0x12, "Importance")
		page.addToken(0x13, "MessageClass")
		page.addToken(0x14, "Subject")
		page.addToken(0x15, "Read")
		page.addToken(0x16, "To")
		page.addToken(0x17, "CC")
		page.addToken(0x18, "From")
		page.addToken(0x19, "ReplyTo")
		page.addToken(0x1A, "AllDayEvent")
		page.addToken(0x1B, "Categories")
		page.addToken(0x1C, "Category")
		page.addToken(0x1D, "DTStamp")
		page.addToken(0x1E, "EndTime")
		page.addToken(0x1F, "InstanceType")
		page.addToken(0x20, "BusyStatus")
		page.addToken(0x21, "Location")
		page.addToken(0x22, "MeetingRequest")
		page.addToken(0x23, "Organizer")
		page.addToken(0x24, "RecurrenceId")
		page.addToken(0x25, "Reminder")
		page.addToken(0x26, "ResponseRequested")
		page.addToken(0x27, "Recurrences")
		page.addToken(0x28, "Recurrence")
		page.addToken(0x29, "Recurrence_Type")
		page.addToken(0x2A, "Recurrence_Until")
		page.addToken(0x2B, "Recurrence_Occurrences")
		page.addToken(0x2C, "Recurrence_Interval")
		page.addToken(0x2D, "Recurrence_DayOfWeek")
		page.addToken(0x2E, "Recurrence_DayOfMonth")
		page.addToken(0x2F, "Recurrence_WeekOfMonth")
		page.addToken(0x30, "Recurrence_MonthOfYear")
		page.addToken(0x31, "StartTime")
		page.addToken(0x32, "Sensitivity")
		page.addToken(0x33, "TimeZone")
		page.addToken(0x34, "GlobalObjId")
		page.addToken(0x35, "ThreadTopic")
		page.addToken(0x39, "InternetCPID")
		page.addToken(0x3A, "Flag")
		page.addToken(0x3B, "FlagStatus")
		page.addToken(0x3C, "ContentClass")
		page.addToken(0x3D, "FlagType")
		page.addToken(0x3E, "CompleteTime")
		page.addToken(0x3F, "DisallowNewTimeProposal")
		self.codePages.append(page)
		# endregion

		# Code Page 3: AirNotify - retired
		# region AirNotify Code Page
		page = ASWBXMLCodePage()
		page.namespace = ""
		page.xmlns = ""
		self.codePages.append(page)
		# endregion

		# Code Page 4: Calendar
		# region Calendar Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Calendar:"
		page.xmlns = "calendar"

		page.addToken(0x05, "TimeZone")
		page.addToken(0x06, "AllDayEvent")
		page.addToken(0x07, "Attendees")
		page.addToken(0x08, "Attendee")
		page.addToken(0x09, "Attendee_Email")
		page.addToken(0x0A, "Attendee_Name")
		page.addToken(0x0D, "BusyStatus")
		page.addToken(0x0E, "Categories")
		page.addToken(0x0F, "Category")
		page.addToken(0x11, "DTStamp")
		page.addToken(0x12, "EndTime")
		page.addToken(0x13, "Exception")
		page.addToken(0x14, "Exceptions")
		page.addToken(0x15, "Exception_Deleted")
		page.addToken(0x16, "Exception_StartTime")
		page.addToken(0x17, "Location")
		page.addToken(0x18, "MeetingStatus")
		page.addToken(0x19, "Organizer_Email")
		page.addToken(0x1A, "Organizer_Name")
		page.addToken(0x1B, "Recurrence")
		page.addToken(0x1C, "Recurrence_Type")
		page.addToken(0x1D, "Recurrence_Until")
		page.addToken(0x1E, "Recurrence_Occurrences")
		page.addToken(0x1F, "Recurrence_Interval")
		page.addToken(0x20, "Recurrence_DayOfWeek")
		page.addToken(0x21, "Recurrence_DayOfMonth")
		page.addToken(0x22, "Recurrence_WeekOfMonth")
		page.addToken(0x23, "Recurrence_MonthOfYear")
		page.addToken(0x24, "Reminder")
		page.addToken(0x25, "Sensitivity")
		page.addToken(0x26, "Subject")
		page.addToken(0x27, "StartTime")
		page.addToken(0x28, "UID")
		page.addToken(0x29, "Attendee_Status")
		page.addToken(0x2A, "Attendee_Type")
		page.addToken(0x33, "DisallowNewTimeProposal")
		page.addToken(0x34, "ResponseRequested")
		page.addToken(0x35, "AppointmentReplyTime")
		page.addToken(0x36, "ResponseType")
		page.addToken(0x37, "CalendarType")
		page.addToken(0x38, "IsLeapMonth")
		page.addToken(0x39, "FirstDayOfWeek")
		page.addToken(0x3A, "OnlineMeetingConfLink")
		page.addToken(0x3B, "OnlineMeetingExternalLink")
		self.codePages.append(page)
		# endregion

		# Code Page 5: Move
		# region Move Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Move:"
		page.xmlns = "move"

		page.addToken(0x05, "MoveItems")
		page.addToken(0x06, "Move")
		page.addToken(0x07, "SrcMsgId")
		page.addToken(0x08, "SrcFldId")
		page.addToken(0x09, "DstFldId")
		page.addToken(0x0A, "Response")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "DstMsgId")
		self.codePages.append(page)
		# endregion

		# Code Page 6: ItemEstimate
		# region ItemEstimate Code Page
		page = ASWBXMLCodePage()
		page.namespace = "GetItemEstimate:"
		page.xmlns = "getitemestimate"

		page.addToken(0x05, "GetItemEstimate")
		page.addToken(0x06, "Version")
		page.addToken(0x07, "Collections")
		page.addToken(0x08, "Collection")
		page.addToken(0x09, "Class")
		page.addToken(0x0A, "CollectionId")
		page.addToken(0x0B, "DateTime")
		page.addToken(0x0C, "Estimate")
		page.addToken(0x0D, "Response")
		page.addToken(0x0E, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 7: FolderHierarchy
		# region FolderHierarchy Code Page
		page = ASWBXMLCodePage()
		page.namespace = "FolderHierarchy:"
		page.xmlns = "folderhierarchy"

		page.addToken(0x07, "DisplayName")
		page.addToken(0x08, "ServerId")
		page.addToken(0x09, "ParentId")
		page.addToken(0x0A, "Type")
		page.addToken(0x0C, "Status")
		page.addToken(0x0E, "Changes")
		page.addToken(0x0F, "Add")
		page.addToken(0x10, "Delete")
		page.addToken(0x11, "Update")
		page.addToken(0x12, "SyncKey")
		page.addToken(0x13, "FolderCreate")
		page.addToken(0x14, "FolderDelete")
		page.addToken(0x15, "FolderUpdate")
		page.addToken(0x16, "FolderSync")
		page.addToken(0x17, "Count")

		self.codePages.append(page)
		# endregion

		# Code Page 8: MeetingResponse
		# region MeetingResponse Code Page
		page = ASWBXMLCodePage()
		page.namespace = "MeetingResponse:"
		page.xmlns = "meetingresponse"

		page.addToken(0x05, "CalendarId")
		page.addToken(0x06, "CollectionId")
		page.addToken(0x07, "MeetingResponse")
		page.addToken(0x08, "RequestId")
		page.addToken(0x09, "Request")
		page.addToken(0x0A, "Result")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "UserResponse")
		page.addToken(0x0E, "InstanceId")
		self.codePages.append(page)
		# endregion

		# Code Page 9: Tasks
		# region Tasks Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Tasks:"
		page.xmlns = "tasks"

		page.addToken(0x08, "Categories")
		page.addToken(0x09, "Category")
		page.addToken(0x0A, "Complete")
		page.addToken(0x0B, "DateCompleted")
		page.addToken(0x0C, "DueDate")
		page.addToken(0x0D, "UTCDueDate")
		page.addToken(0x0E, "Importance")
		page.addToken(0x0F, "Recurrence")
		page.addToken(0x10, "Recurrence_Type")
		page.addToken(0x11, "Recurrence_Start")
		page.addToken(0x12, "Recurrence_Until")
		page.addToken(0x13, "Recurrence_Occurrences")
		page.addToken(0x14, "Recurrence_Interval")
		page.addToken(0x15, "Recurrence_DayOfMonth")
		page.addToken(0x16, "Recurrence_DayOfWeek")
		page.addToken(0x17, "Recurrence_WeekOfMonth")
		page.addToken(0x18, "Recurrence_MonthOfYear")
		page.addToken(0x19, "Recurrence_Regenerate")
		page.addToken(0x1A, "Recurrence_DeadOccur")
		page.addToken(0x1B, "ReminderSet")
		page.addToken(0x1C, "ReminderTime")
		page.addToken(0x1D, "Sensitivity")
		page.addToken(0x1E, "StartDate")
		page.addToken(0x1F, "UTCStartDate")
		page.addToken(0x20, "Subject")
		page.addToken(0x22, "OrdinalDate")
		page.addToken(0x23, "SubOrdinalDate")
		page.addToken(0x24, "CalendarType")
		page.addToken(0x25, "IsLeapMonth")
		page.addToken(0x26, "FirstDayOfWeek")
		self.codePages.append(page)
		# endregion

		# Code Page 10: ResolveRecipients
		# region ResolveRecipients Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ResolveRecipients:"
		page.xmlns = "resolverecipients"

		page.addToken(0x05, "ResolveRecipients")
		page.addToken(0x06, "Response")
		page.addToken(0x07, "Status")
		page.addToken(0x08, "Type")
		page.addToken(0x09, "Recipient")
		page.addToken(0x0A, "DisplayName")
		page.addToken(0x0B, "EmailAddress")
		page.addToken(0x0C, "Certificates")
		page.addToken(0x0D, "Certificate")
		page.addToken(0x0E, "MiniCertificate")
		page.addToken(0x0F, "Options")
		page.addToken(0x10, "To")
		page.addToken(0x11, "CertificateRetrieval")
		page.addToken(0x12, "RecipientCount")
		page.addToken(0x13, "MaxCertificates")
		page.addToken(0x14, "MaxAmbiguousRecipients")
		page.addToken(0x15, "CertificateCount")
		page.addToken(0x16, "Availability")
		page.addToken(0x17, "StartTime")
		page.addToken(0x18, "EndTime")
		page.addToken(0x19, "MergedFreeBusy")
		page.addToken(0x1A, "Picture")
		page.addToken(0x1B, "MaxSize")
		page.addToken(0x1C, "Data")
		page.addToken(0x1D, "MaxPictures")
		self.codePages.append(page)
		# endregion

		# Code Page 11: ValidateCert
		# region ValidateCert Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ValidateCert:"
		page.xmlns = "validatecert"

		page.addToken(0x05, "ValidateCert")
		page.addToken(0x06, "Certificates")
		page.addToken(0x07, "Certificate")
		page.addToken(0x08, "CertificateChain")
		page.addToken(0x09, "CheckCRL")
		page.addToken(0x0A, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 12: Contacts2
		# region Contacts2 Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Contacts2:"
		page.xmlns = "contacts2"

		page.addToken(0x05, "CustomerId")
		page.addToken(0x06, "GovernmentId")
		page.addToken(0x07, "IMAddress")
		page.addToken(0x08, "IMAddress2")
		page.addToken(0x09, "IMAddress3")
		page.addToken(0x0A, "ManagerName")
		page.addToken(0x0B, "CompanyMainPhone")
		page.addToken(0x0C, "AccountName")
		page.addToken(0x0D, "NickName")
		page.addToken(0x0E, "MMS")
		self.codePages.append(page)
		# endregion

		# Code Page 13: Ping
		# region Ping Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Ping:"
		page.xmlns = "ping"

		page.addToken(0x05, "Ping")
		page.addToken(0x06, "AutdState")  # Per MS-ASWBXML, this tag is not used by protocol
		page.addToken(0x07, "Status")
		page.addToken(0x08, "HeartbeatInterval")
		page.addToken(0x09, "Folders")
		page.addToken(0x0A, "Folder")
		page.addToken(0x0B, "Id")
		page.addToken(0x0C, "Class")
		page.addToken(0x0D, "MaxFolders")
		self.codePages.append(page)
		# endregion

		# Code Page 14: Provision
		# region Provision Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Provision:"
		page.xmlns = "provision"

		page.addToken(0x05, "Provision")
		page.addToken(0x06, "Policies")
		page.addToken(0x07, "Policy")
		page.addToken(0x08, "PolicyType")
		page.addToken(0x09, "PolicyKey")
		page.addToken(0x0A, "Data")
		page.addToken(0x0B, "Status")
		page.addToken(0x0C, "RemoteWipe")
		page.addToken(0x0D, "EASProvisionDoc")
		page.addToken(0x0E, "DevicePasswordEnabled")
		page.addToken(0x0F, "AlphanumericDevicePasswordRequired")
		page.addToken(0x10, "RequireStorageCardEncryption")
		page.addToken(0x11, "PasswordRecoveryEnabled")
		page.addToken(0x13, "AttachmentsEnabled")
		page.addToken(0x14, "MinDevicePasswordLength")
		page.addToken(0x15, "MaxInactivityTimeDeviceLock")
		page.addToken(0x16, "MaxDevicePasswordFailedAttempts")
		page.addToken(0x17, "MaxAttachmentSize")
		page.addToken(0x18, "AllowSimpleDevicePassword")
		page.addToken(0x19, "DevicePasswordExpiration")
		page.addToken(0x1A, "DevicePasswordHistory")
		page.addToken(0x1B, "AllowStorageCard")
		page.addToken(0x1C, "AllowCamera")
		page.addToken(0x1D, "RequireDeviceEncryption")
		page.addToken(0x1E, "AllowUnsignedApplications")
		page.addToken(0x1F, "AllowUnsignedInstallationPackages")
		page.addToken(0x20, "MinDevicePasswordComplexCharacters")
		page.addToken(0x21, "AllowWiFi")
		page.addToken(0x22, "AllowTextMessaging")
		page.addToken(0x23, "AllowPOPIMAPEmail")
		page.addToken(0x24, "AllowBluetooth")
		page.addToken(0x25, "AllowIrDA")
		page.addToken(0x26, "RequireManualSyncWhenRoaming")
		page.addToken(0x27, "AllowDesktopSync")
		page.addToken(0x28, "MaxCalendarAgeFilter")
		page.addToken(0x29, "AllowHTMLEmail")
		page.addToken(0x2A, "MaxEmailAgeFilter")
		page.addToken(0x2B, "MaxEmailBodyTruncationSize")
		page.addToken(0x2C, "MaxEmailHTMLBodyTruncationSize")
		page.addToken(0x2D, "RequireSignedSMIMEMessages")
		page.addToken(0x2E, "RequireEncryptedSMIMEMessages")
		page.addToken(0x2F, "RequireSignedSMIMEAlgorithm")
		page.addToken(0x30, "RequireEncryptionSMIMEAlgorithm")
		page.addToken(0x31, "AllowSMIMEEncryptionAlgorithmNegotiation")
		page.addToken(0x32, "AllowSMIMESoftCerts")
		page.addToken(0x33, "AllowBrowser")
		page.addToken(0x34, "AllowConsumerEmail")
		page.addToken(0x35, "AllowRemoteDesktop")
		page.addToken(0x36, "AllowInternetSharing")
		page.addToken(0x37, "UnapprovedInROMApplicationList")
		page.addToken(0x38, "ApplicationName")
		page.addToken(0x39, "ApprovedApplicationList")
		page.addToken(0x3A, "Hash")
		self.codePages.append(page)
		# endregion

		# Code Page 15: Search
		# region Search Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Search:"
		page.xmlns = "search"

		page.addToken(0x05, "Search")
		page.addToken(0x07, "Store")
		page.addToken(0x08, "Name")
		page.addToken(0x09, "Query")
		page.addToken(0x0A, "Options")
		page.addToken(0x0B, "Range")
		page.addToken(0x0C, "Status")
		page.addToken(0x0D, "Response")
		page.addToken(0x0E, "Result")
		page.addToken(0x0F, "Properties")
		page.addToken(0x10, "Total")
		page.addToken(0x11, "EqualTo")
		page.addToken(0x12, "Value")
		page.addToken(0x13, "And")
		page.addToken(0x14, "Or")
		page.addToken(0x15, "FreeText")
		page.addToken(0x17, "DeepTraversal")
		page.addToken(0x18, "LongId")
		page.addToken(0x19, "RebuildResults")
		page.addToken(0x1A, "LessThan")
		page.addToken(0x1B, "GreaterThan")
		page.addToken(0x1E, "UserName")
		page.addToken(0x1F, "Password")
		page.addToken(0x20, "ConversationId")
		page.addToken(0x21, "Picture")
		page.addToken(0x22, "MaxSize")
		page.addToken(0x23, "MaxPictures")
		self.codePages.append(page)
		# endregion

		# Code Page 16: GAL
		# region GAL Code Page
		page = ASWBXMLCodePage()
		page.namespace = "GAL:"
		page.xmlns = "gal"

		page.addToken(0x05, "DisplayName")
		page.addToken(0x06, "Phone")
		page.addToken(0x07, "Office")
		page.addToken(0x08, "Title")
		page.addToken(0x09, "Company")
		page.addToken(0x0A, "Alias")
		page.addToken(0x0B, "FirstName")
		page.addToken(0x0C, "LastName")
		page.addToken(0x0D, "HomePhone")
		page.addToken(0x0E, "MobilePhone")
		page.addToken(0x0F, "EmailAddress")
		page.addToken(0x10, "Picture")
		page.addToken(0x11, "Status")
		page.addToken(0x12, "Data")
		self.codePages.append(page)
		# endregion

		# Code Page 17: AirSyncBase
		# region AirSyncBase Code Page
		page = ASWBXMLCodePage()
		page.namespace = "AirSyncBase:"
		page.xmlns = "airsyncbase"

		page.addToken(0x05, "BodyPreference")
		page.addToken(0x06, "Type")
		page.addToken(0x07, "TruncationSize")
		page.addToken(0x08, "AllOrNone")
		page.addToken(0x0A, "Body")
		page.addToken(0x0B, "Data")
		page.addToken(0x0C, "EstimatedDataSize")
		page.addToken(0x0D, "Truncated")
		page.addToken(0x0E, "Attachments")
		page.addToken(0x0F, "Attachment")
		page.addToken(0x10, "DisplayName")
		page.addToken(0x11, "FileReference")
		page.addToken(0x12, "Method")
		page.addToken(0x13, "ContentId")
		page.addToken(0x14, "ContentLocation")
		page.addToken(0x15, "IsInline")
		page.addToken(0x16, "NativeBodyType")
		page.addToken(0x17, "ContentType")
		page.addToken(0x18, "Preview")
		page.addToken(0x19, "BodyPartPreference")
		page.addToken(0x1A, "BodyPart")
		page.addToken(0x1B, "Status")
		self.codePages.append(page)
		# endregion

		# Code Page 18: Settings
		# region Settings Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Settings:"
		page.xmlns = "settings"

		page.addToken(0x05, "Settings")
		page.addToken(0x06, "Status")
		page.addToken(0x07, "Get")
		page.addToken(0x08, "Set")
		page.addToken(0x09, "Oof")
		page.addToken(0x0A, "OofState")
		page.addToken(0x0B, "StartTime")
		page.addToken(0x0C, "EndTime")
		page.addToken(0x0D, "OofMessage")
		page.addToken(0x0E, "AppliesToInternal")
		page.addToken(0x0F, "AppliesToExternalKnown")
		page.addToken(0x10, "AppliesToExternalUnknown")
		page.addToken(0x11, "Enabled")
		page.addToken(0x12, "ReplyMessage")
		page.addToken(0x13, "BodyType")
		page.addToken(0x14, "DevicePassword")
		page.addToken(0x15, "Password")
		page.addToken(0x16, "DeviceInformation")
		page.addToken(0x17, "Model")
		page.addToken(0x18, "IMEI")
		page.addToken(0x19, "FriendlyName")
		page.addToken(0x1A, "OS")
		page.addToken(0x1B, "OSLanguage")
		page.addToken(0x1C, "PhoneNumber")
		page.addToken(0x1D, "UserInformation")
		page.addToken(0x1E, "EmailAddresses")
		page.addToken(0x1F, "SmtpAddress")
		page.addToken(0x20, "UserAgent")
		page.addToken(0x21, "EnableOutboundSMS")
		page.addToken(0x22, "MobileOperator")
		page.addToken(0x23, "PrimarySmtpAddress")
		page.addToken(0x24, "Accounts")
		page.addToken(0x25, "Account")
		page.addToken(0x26, "AccountId")
		page.addToken(0x27, "AccountName")
		page.addToken(0x28, "UserDisplayName")
		page.addToken(0x29, "SendDisabled")
		page.addToken(0x2B, "RightsManagementInformation")
		self.codePages.append(page)
		# endregion

		# Code Page 19: DocumentLibrary
		# region DocumentLibrary Code Page
		page = ASWBXMLCodePage()
		page.namespace = "DocumentLibrary:"
		page.xmlns = "documentlibrary"

		page.addToken(0x05, "LinkId")
		page.addToken(0x06, "DisplayName")
		page.addToken(0x07, "IsFolder")
		page.addToken(0x08, "CreationDate")
		page.addToken(0x09, "LastModifiedDate")
		page.addToken(0x0A, "IsHidden")
		page.addToken(0x0B, "ContentLength")
		page.addToken(0x0C, "ContentType")
		self.codePages.append(page)
		# endregion

		# Code Page 20: ItemOperations
		# region ItemOperations Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ItemOperations:"
		page.xmlns = "itemoperations"

		page.addToken(0x05, "ItemOperations")
		page.addToken(0x06, "Fetch")
		page.addToken(0x07, "Store")
		page.addToken(0x08, "Options")
		page.addToken(0x09, "Range")
		page.addToken(0x0A, "Total")
		page.addToken(0x0B, "Properties")
		page.addToken(0x0C, "Data")
		page.addToken(0x0D, "Status")
		page.addToken(0x0E, "Response")
		page.addToken(0x0F, "Version")
		page.addToken(0x10, "Schema")
		page.addToken(0x11, "Part")
		page.addToken(0x12, "EmptyFolderContents")
		page.addToken(0x13, "DeleteSubFolders")
		page.addToken(0x14, "UserName")
		page.addToken(0x15, "Password")
		page.addToken(0x16, "Move")
		page.addToken(0x17, "DstFldId")
		page.addToken(0x18, "ConversationId")
		page.addToken(0x19, "MoveAlways")
		self.codePages.append(page)
		# endregion

		# Code Page 21: ComposeMail
		# region ComposeMail Code Page
		page = ASWBXMLCodePage()
		page.namespace = "ComposeMail:"
		page.xmlns = "composemail"

		page.addToken(0x05, "SendMail")
		page.addToken(0x06, "SmartForward")
		page.addToken(0x07, "SmartReply")
		page.addToken(0x08, "SaveInSentItems")
		page.addToken(0x09, "ReplaceMime")
		page.addToken(0x0B, "Source")
		page.addToken(0x0C, "FolderId")
		page.addToken(0x0D, "ItemId")
		page.addToken(0x0E, "LongId")
		page.addToken(0x0F, "InstanceId")
		page.addToken(0x10, "MIME")
		page.addToken(0x11, "ClientId")
		page.addToken(0x12, "Status")
		page.addToken(0x13, "AccountId")
		self.codePages.append(page)
		# endregion

		# Code Page 22: Email2
		# region Email2 Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Email2:"
		page.xmlns = "email2"

		page.addToken(0x05, "UmCallerID")
		page.addToken(0x06, "UmUserNotes")
		page.addToken(0x07, "UmAttDuration")
		page.addToken(0x08, "UmAttOrder")
		page.addToken(0x09, "ConversationId")
		page.addToken(0x0A, "ConversationIndex")
		page.addToken(0x0B, "LastVerbExecuted")
		page.addToken(0x0C, "LastVerbExecutionTime")
		page.addToken(0x0D, "ReceivedAsBcc")
		page.addToken(0x0E, "Sender")
		page.addToken(0x0F, "CalendarType")
		page.addToken(0x10, "IsLeapMonth")
		page.addToken(0x11, "AccountId")
		page.addToken(0x12, "FirstDayOfWeek")
		page.addToken(0x13, "MeetingMessageType")
		self.codePages.append(page)
		# endregion

		# Code Page 23: Notes
		# region Notes Code Page
		page = ASWBXMLCodePage()
		page.namespace = "Notes:"
		page.xmlns = "notes"

		page.addToken(0x05, "Subject")
		page.addToken(0x06, "MessageClass")
		page.addToken(0x07, "LastModifiedDate")
		page.addToken(0x08, "Categories")
		page.addToken(0x09, "Category")
		self.codePages.append(page)
		# endregion

		# Code Page 24: RightsManagement
		# region RightsManagement Code Page
		page = ASWBXMLCodePage()
		page.namespace = "RightsManagement:"
		page.xmlns = "rightsmanagement"

		page.addToken(0x05, "RightsManagementSupport")
		page.addToken(0x06, "RightsManagementTemplates")
		page.addToken(0x07, "RightsManagementTemplate")
		page.addToken(0x08, "RightsManagementLicense")
		page.addToken(0x09, "EditAllowed")
		page.addToken(0x0A, "ReplyAllowed")
		page.addToken(0x0B, "ReplyAllAllowed")
		page.addToken(0x0C, "ForwardAllowed")
		page.addToken(0x0D, "ModifyRecipientsAllowed")
		page.addToken(0x0E, "ExtractAllowed")
		page.addToken(0x0F, "PrintAllowed")
		page.addToken(0x10, "ExportAllowed")
		page.addToken(0x11, "ProgrammaticAccessAllowed")
		page.addToken(0x12, "RMOwner")
		page.addToken(0x13, "ContentExpiryDate")
		page.addToken(0x14, "TemplateID")
		page.addToken(0x15, "TemplateName")
		page.addToken(0x16, "TemplateDescription")
		page.addToken(0x17, "ContentOwner")
		page.addToken(0x18, "RemoveRightsManagementDistribution")
		self.codePages.append(page)
		# endregion
		# endregion
	
	def loadXml(self, strXML):
		# note xmlDoc has .childNodes and .parentNode
		self.xmlDoc = xml.dom.minidom.parseString(strXML)

	def getXml(self):
		if (self.xmlDoc != None):
			try:
				return self.xmlDoc.toprettyxml(indent="    ", newl="\n")
			except:
				return self.xmlDoc.toxml()
	
	def loadBytes(self, byteWBXML):
		
		currentNode = self.xmlDoc
		
		wbXMLBytes = ASWBXMLByteQueue(byteWBXML)
		# Version is ignored
		version = wbXMLBytes.dequeueAndLog()

		# Public Identifier is ignored
		publicId = wbXMLBytes.dequeueMultibyteInt()
		
		logging.debug("Version: %d, Public Identifier: %d" % (version, publicId))
		
		# Character set
		# Currently only UTF-8 is supported, throw if something else
		charset = wbXMLBytes.dequeueMultibyteInt()
		if (charset != 0x6A):
			raise InvalidDataException("ASWBXML only supports UTF-8 encoded XML.")

		# String table length
		# This should be 0, MS-ASWBXML does not use string tables
		stringTableLength = wbXMLBytes.dequeueMultibyteInt()
		if (stringTableLength != 0):
			raise InvalidDataException("WBXML data contains a string table.")

		# Now we should be at the body of the data.
		# Add the declaration
		unusedArray = [GlobalTokens.ENTITY, GlobalTokens.EXT_0, GlobalTokens.EXT_1, GlobalTokens.EXT_2, GlobalTokens.EXT_I_0, GlobalTokens.EXT_I_1, GlobalTokens.EXT_I_2, GlobalTokens.EXT_T_0, GlobalTokens.EXT_T_1, GlobalTokens.EXT_T_2, GlobalTokens.LITERAL, GlobalTokens.LITERAL_A, GlobalTokens.LITERAL_AC, GlobalTokens.LITERAL_C, GlobalTokens.PI, GlobalTokens.STR_T]
		
		while ( wbXMLBytes.qsize() > 0):
			currentByte = wbXMLBytes.dequeueAndLog()
			if ( currentByte == GlobalTokens.SWITCH_PAGE ):
				newCodePage = wbXMLBytes.dequeueAndLog()
				if (newCodePage >= 0 and newCodePage < 25):
					self.currentCodePage = newCodePage
				else:
					raise InvalidDataException("Unknown code page ID 0x{0:X} encountered in WBXML".format(currentByte))
			elif  ( currentByte == GlobalTokens.END ):
				if (currentNode != None and currentNode.parentNode != None):
					currentNode = currentNode.parentNode
				else:
					raise InvalidDataException("END global token encountered out of sequence")
					break
			elif  ( currentByte == GlobalTokens.OPAQUE ):
				CDATALength = wbXMLBytes.dequeueMultibyteInt()
				newOpaqueNode = self.xmlDoc.createCDATASection(wbXMLBytes.dequeueString(CDATALength))
				currentNode.appendChild(newOpaqueNode)

			elif  ( currentByte == GlobalTokens.STR_I ):
				newTextNode = self.xmlDoc.createTextNode(wbXMLBytes.dequeueString())
				currentNode.appendChild(newTextNode)

			elif ( currentByte in unusedArray):
				raise InvalidDataException("Encountered unknown global token 0x{0:X}.".format(currentByte))
			else:
				hasAttributes = (currentByte & 0x80) > 0
				hasContent = (currentByte & 0x40) > 0

				token = currentByte & 0x3F
				if (hasAttributes):
					raise InvalidDataException("Token 0x{0:X} has attributes.".format(token))

				strTag = self.codePages[self.currentCodePage].getTag(token)
				if (strTag == None):
					strTag = "UNKNOWN_TAG_{0,2:X}".format(token)

				newNode = self.xmlDoc.createElement(strTag)
				# not sure if this should be set on every node or not
				#newNode.setAttribute("xmlns", self.codePages[self.currentCodePage].xmlns)
				
				currentNode.appendChild(newNode)

				if (hasContent):
					currentNode = newNode

		logging.debug("Total bytes dequeued: %d" % wbXMLBytes.bytesDequeued)

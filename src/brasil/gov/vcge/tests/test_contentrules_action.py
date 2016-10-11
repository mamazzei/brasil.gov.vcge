# -*- coding:utf-8 -*-
from brasil.gov.vcge.contentrules.action import VCGEAction
from brasil.gov.vcge.contentrules.action import VCGEEditForm
from brasil.gov.vcge.testing import INTEGRATION_TESTING
from plone import api
from plone.app.contentrules.rule import Rule
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IExecutable
from plone.contentrules.rule.interfaces import IRuleAction
from Products.CMFCore.PortalContent import PortalContent
from Products.CMFCore.PortalFolder import PortalFolder
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component.interfaces import IObjectEvent
from zope.interface import implementer

import unittest2 as unittest


@implementer(IObjectEvent)
class DummyEvent(object):

    def __init__(self, object):
        self.object = object


class TestSubjectAction(unittest.TestCase):

    layer = INTEGRATION_TESTING

    term = 'http://vocab.e.gov.br/id/governo#cultura'

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])

        self.folder = api.content.create(
            type='Folder',
            container=self.portal,
            id='folder'
        )
        self.folder.skos = [self.term, ]
        self.folder.reindexObject()

        self.sub_folder = api.content.create(
            type='Folder',
            container=self.folder,
            id='sub_folder'
        )

        self.document = api.content.create(
            type='Document',
            container=self.folder,
            id='a_document'
        )
        self.document.setSubject(['Bar', ])
        self.document.reindexObject()

        o = PortalContent('cmf', 'CMF Content', '', '', '')
        self.folder._setObject('cmf', o, suppress_events=True)
        o = PortalFolder('cmf_folder', 'CMF Folder', '')
        self.folder._setObject('cmf_folder', o, suppress_events=True)
        o = PortalContent('cmf', 'CMF Content', '', '', '')
        self.folder['cmf_folder']._setObject('cmf', o, suppress_events=True)

    def test_registered(self):
        element = getUtility(IRuleAction,
                             name='brasil.gov.vcge.actions.VCGE')
        self.assertEqual('brasil.gov.vcge.actions.VCGE', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)

    def test_invoke_add_view(self):
        element = getUtility(IRuleAction,
                             name='brasil.gov.vcge.actions.VCGE')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')

        adding = getMultiAdapter((rule, self.portal.REQUEST),
                                 name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST),
                                  name=element.addview)

        addview.createAndAdd(data={'same_as_parent': False,
                                   'skos': [self.term, ]})

        e = rule.actions[0]
        self.assertTrue(isinstance(e, VCGEAction))
        self.assertEqual(False, e.same_as_parent)
        self.assertEqual([self.term, ], e.skos)

    def test_invoke_edit_view(self):
        element = getUtility(IRuleAction,
                             name='brasil.gov.vcge.actions.VCGE')
        e = VCGEAction()
        editview = getMultiAdapter((e, self.folder.REQUEST),
                                   name=element.editview)
        self.assertTrue(isinstance(editview, VCGEEditForm))

    def test_summary_parent_vcge(self):
        e = VCGEAction()
        e.same_as_parent = True
        self.assertEqual(
            e.summary,
            u'Aplica termos da pasta no conteúdo.'
        )

    def test_summary_with_vcge(self):
        from plone.app.contentrules import PloneMessageFactory as _
        e = VCGEAction()
        e.skos = [self.term, ]
        msg = _(u'Aplica os termos ${skos}',
                mapping=dict(skos=' or '.join(e.skos)))
        self.assertEqual(
            e.summary,
            msg
        )

    def test_execute_with_vcge(self):
        e = VCGEAction()
        e.same_as_parent = False
        e.skos = ['http://vocab.e.gov.br/2011/03/vcge#governo', ]

        ex = getMultiAdapter((self.folder, e,
                             DummyEvent(self.sub_folder)),
                             IExecutable)
        self.assertEqual(True, ex())

        self.assertEqual(list(self.sub_folder.skos), e.skos)

    def test_execute_same_as_parent(self):
        e = VCGEAction()
        e.same_as_parent = True
        e.skos = []

        ex = getMultiAdapter((self.folder, e,
                             DummyEvent(self.sub_folder)),
                             IExecutable)
        self.assertEqual(True, ex())

        self.assertEqual(self.sub_folder.skos, self.folder.skos)

    def test_execute_object_without_vcge(self):
        e = VCGEAction()
        e.same_as_parent = False
        e.skos = ['http://vocab.e.gov.br/2011/03/vcge#governo', ]
        o = self.folder['cmf']
        ex = getMultiAdapter((self.folder, e,
                             DummyEvent(o)),
                             IExecutable)
        self.assertEqual(False, ex())

    def test_execute_parent_without_vcge(self):
        e = VCGEAction()
        e.same_as_parent = True
        e.skos = []
        folder = self.folder['cmf_folder']
        o = folder['cmf']
        ex = getMultiAdapter((folder, e,
                             DummyEvent(o)),
                             IExecutable)
        self.assertEqual(False, ex())

    def test_execute_parent_without_vcge_attribute(self):
        e = VCGEAction()
        e.same_as_parent = True
        e.skos = []
        delattr(self.folder, 'skos')
        ex = getMultiAdapter((self.folder, e,
                             DummyEvent(self.sub_folder)),
                             IExecutable)
        self.assertEqual(False, ex())
